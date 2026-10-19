import type { HexagramSummary, LearningGuide } from './types'
import guideContent from './data/learning_guides.json'
import approvalContent from './data/learning_approvals.json'
export type LearningGroup = 'all' | 'upper' | 'lower'
export function filterHexagrams(
  entries: HexagramSummary[],
  search: string,
  group: LearningGroup,
) {
  const query = search.trim().toLocaleLowerCase()
  return entries
    .filter(
      (entry) =>
        (group === 'all' ||
          (group === 'upper'
            ? entry.wenwang_order <= 30
            : entry.wenwang_order > 30)) &&
        (!query ||
          `${entry.name} ${entry.title} ${entry.upper_trigram.name} ${entry.lower_trigram.name}`
            .toLocaleLowerCase()
            .includes(query) ||
          (/^\d+$/.test(query) && Number(query) === entry.wenwang_order)),
    )
    .sort((a, b) => a.wenwang_order - b.wenwang_order)
}
// Independent editorial layer. Add content only after source checking and human review.
const learningGuides: LearningGuide[] = guideContent as LearningGuide[]
// A status flag alone is not publication authorization; require a tracked approval.
const approvedIds = new Set(approvalContent.approved.map((entry) => entry.hexagram_id))
export function reviewedGuide(id: number): LearningGuide | undefined {
  return learningGuides.find(
    (guide) => guide.hexagram_id === id && guide.review_status === 'reviewed' && approvedIds.has(id),
  )
}
