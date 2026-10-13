import type { HistorySummary } from './types'

export type HistoryAIFilter = 'all' | 'with-ai' | 'without-ai'

export function filterHistoryRecords(
  records: HistorySummary[], query: string, aiFilter: HistoryAIFilter,
): HistorySummary[] {
  const normalizedQuery = query.trim().toLocaleLowerCase()
  return records.filter((record) => {
    const matchesQuery = !normalizedQuery || record.question.toLocaleLowerCase().includes(normalizedQuery)
    const hasAI = record.has_ai_sessions === true
    const matchesAI = aiFilter === 'all' || (aiFilter === 'with-ai' ? hasAI : !hasAI)
    return matchesQuery && matchesAI
  })
}
