import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import approvals from './data/learning_approvals.json'
import guides from './data/learning_guides.json'
import { reviewedGuide } from './learning'

describe('editorial approval ledger and publication safety', () => {
  it('records uniquely attributable human approval decisions', () => {
    expect(approvals.schema_version).toBe(1)
    const ids = approvals.approved.map((entry) => entry.hexagram_id)
    expect(ids).toEqual([...ids].sort((a, b) => a - b))
    expect(new Set(ids).size).toBe(ids.length)
    for (const entry of approvals.approved) {
      expect(Number.isInteger(entry.hexagram_id)).toBe(true)
      expect(entry.hexagram_id).toBeGreaterThanOrEqual(1)
      expect(entry.hexagram_id).toBeLessThanOrEqual(64)
      expect(entry.approval_pr).toMatch(/^https:\/\/github\.com\/Qiuizi\/yijing-workbench-public\/pull\/\d+$/)
      expect(entry.approved_on).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      expect(Number.isNaN(Date.parse(entry.approved_on))).toBe(false)
      expect(entry.audit_document).toMatch(/^docs\/learning-guides-review-[\d-]+\.md$/)
      const document = readFileSync(new URL(`../../${entry.audit_document}`, import.meta.url), 'utf8')
      expect(document.trim().length).toBeGreaterThan(200)
    }
  })

  it('requires both a recorded approval and reviewed status to show editorial text', () => {
    const approvedIds = new Set(approvals.approved.map((entry) => entry.hexagram_id))
    expect(guides).toHaveLength(64)
    for (let id = 1; id <= 64; id++) {
      const guide = guides[id - 1]!
      expect(guide.hexagram_id).toBe(id)
      expect(guide.review_status).toBe(approvedIds.has(id) ? 'reviewed' : 'draft')
      expect(reviewedGuide(id)?.hexagram_id).toBe(approvedIds.has(id) ? id : undefined)
    }
    expect(reviewedGuide(0)).toBeUndefined()
    expect(reviewedGuide(65)).toBeUndefined()
  })
})
