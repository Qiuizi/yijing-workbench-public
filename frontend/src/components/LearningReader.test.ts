import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import catalog from '../../../backend/data/hexagrams.json'
import type { Hexagram, LearningGuide } from '../types'
import LearningReader from './LearningReader.vue'
import LearningHeader from './LearningHeader.vue'
async function render(hexagram: Hexagram, guide?: LearningGuide) {
  return renderToString(createSSRApp(LearningReader, { hexagram, guide }))
}
describe('editorial learning reader', () => {
  it('preserves the complete classical text, pinned revision and correct special lines for all 64 entries', async () => {
    for (const hexagram of catalog) {
      const html = await render(hexagram as Hexagram)
      expect(html).toContain(hexagram.judgment)
      for (const line of hexagram.line_texts) expect(html).toContain(line)
      expect(html).toContain(String(hexagram.source_revision_id))
      expect(html.match(/class="learning-reader__line-text"/g)).toHaveLength(
        hexagram.wenwang_order <= 2 ? 7 : 6,
      )
      expect(html).toContain('导读整理中')
      expect(html).toContain('返回六十四卦')
    }
  })
  it('never presents a draft guide as an approved interpretation', async () => {
    const draft: LearningGuide = {
      hexagram_id: 1,
      one_liner: '测试',
      overview: '未审核测试内容不得发布',
      line_guides: {},
      editorial_version: 'test',
      references: [],
      review_status: 'draft',
    }
    expect(await render(catalog[0] as Hexagram, draft)).not.toContain(
      draft.overview,
    )
    expect(
      await render(catalog[0] as Hexagram, {
        ...draft,
        review_status: 'reviewed',
      }),
    ).toContain(draft.overview)
  })
  it('keeps all four navigation destinations available in the learning header', async () => {
    const html = await renderToString(createSSRApp(LearningHeader))
    expect(html.match(/<button/g)).toHaveLength(4)
    for (const label of ['起卦', '学习', '历史', '设置'])
      expect(html).toContain(label)
    expect(html).toContain('aria-current="page"')
  })
})
