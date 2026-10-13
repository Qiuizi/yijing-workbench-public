import type { AIFailedRequest } from './types'
import type { AIRetryAction } from './aiMessageModel'
export { mergeCompletedAiResult, mergeRefreshedAiSession } from './aiMessageModel'
export type { AIRetryAction } from './aiMessageModel'

/** Reuse the persisted request identity so retrying cannot duplicate a committed answer. */
export function retryActionFromFailure(failed: AIFailedRequest): AIRetryAction {
  return {
    kind: failed.regenerate_from_message_id === null ? 'send' : 'regenerate',
    message: failed.message_text,
    requestId: failed.request_id,
    regenerateFromMessageId: failed.regenerate_from_message_id ?? undefined,
  }
}
