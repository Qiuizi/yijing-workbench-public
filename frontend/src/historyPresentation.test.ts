import { describe, expect, it } from 'vitest'
import { filterHistoryRecords } from './historyPresentation'
import type { HistorySummary } from './types'

const records: HistorySummary[] = [
  { id: 1, question: 'synthetic question alpha', method: 'coins', base_name: '乾', changed_name: '姤', moving_positions: [1], created_at: '2026-01-01T00:00:00Z', has_ai_sessions: true },
  { id: 2, question: 'synthetic question beta', method: 'manual', base_name: '坤', changed_name: '坤', moving_positions: [], created_at: '2026-01-02T00:00:00Z', has_ai_sessions: false },
  { id: 3, question: 'legacy entry', method: 'coins', base_name: '谦', changed_name: '谦', moving_positions: [], created_at: '2026-01-03T00:00:00Z' },
]

describe('history filters', () => {
  it('filters question keywords case-insensitively without changing records', () => {
    expect(filterHistoryRecords(records, ' ALPHA ', 'all').map((record) => record.id)).toEqual([1])
    expect(records).toHaveLength(3)
  })

  it('filters records with and without AI sessions and treats old missing flags as no AI', () => {
    expect(filterHistoryRecords(records, '', 'with-ai').map((record) => record.id)).toEqual([1])
    expect(filterHistoryRecords(records, '', 'without-ai').map((record) => record.id)).toEqual([2, 3])
  })

  it('returns an empty list for a non-matching query', () => {
    expect(filterHistoryRecords(records, 'not present', 'all')).toEqual([])
  })
})
