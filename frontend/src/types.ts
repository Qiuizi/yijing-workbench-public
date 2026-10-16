export interface Trigram {
  name: string
  symbol: string
  binary_code: string
  image: string
}

export interface SpecialLine {
  name: '用九' | '用六'
  text: string
  source_url: string
}

export interface Hexagram {
  wenwang_order: number
  name: string
  title: string
  binary_code: string
  upper_trigram: Trigram
  lower_trigram: Trigram
  judgment: string
  line_texts: string[]
  source_revision_id: number | null
  special_line: SpecialLine | null
  text_source: string
  source_url: string
}

export interface DivinationLine {
  position: number
  value: number
  yin_yang: '阴' | '阳'
  changing: boolean
  coins: number[] | null
}

export interface Divination {
  id: number | null
  question: string
  method: 'coins' | 'manual'
  lines: DivinationLine[]
  changed_lines: DivinationLine[]
  moving_positions: number[]
  base_hexagram: Hexagram
  changed_hexagram: Hexagram
  created_at: string | null
  traditional_reading: TraditionalReading | null
  najia_chart?: NajiaChart | null
  ai_sessions?: AiSessionSummary[]
}

export interface ReadingPassage {
  kind: 'judgment' | 'line' | 'special_line'
  hexagram_order: number
  hexagram_title: string
  label: string
  text: string
  line_position: number | null
  primary: boolean
  source_url: string
  source_revision_id: number | null
}

export interface TraditionalReading {
  ruleset_id: string
  ruleset_version: string
  ruleset_name: string
  source_title: string
  source_url: string
  source_revision_id: number
  moving_count: number
  passages: ReadingPassage[]
  rationale: string
  plain_rule_explanation: string
  interpretation_limit: string
}

export interface NajiaSource {
  scope: string
  title: string
  url: string
  revision_id: number
}

export interface NajiaLine {
  position: number
  yin_yang: '阴' | '阳'
  moving: boolean
  stem: string
  branch: string
  element: string
  relative: string
  spirit: string | null
  role: '世' | '应' | null
  hidden_relative: string | null
  hidden_stem: string | null
  hidden_branch: string | null
  hidden_element: string | null
  flying_relative: string | null
  xunkong: boolean
  month_build: boolean
}

export interface NajiaChart {
  sources: NajiaSource[]
  palace: string
  palace_element: string
  palace_position: string
  world_position: number
  response_position: number
  day_ganzhi: string
  xunkong: string[]
  month_branch: string
  base: NajiaBoard
  changed: NajiaBoard
  rules_note: string
  timestamp_source: 'manual' | 'automatic'
  calendar_context: CalendarContext | null
  rule_analysis?: NajiaRuleAnalysis | null
}

export interface NajiaRuleModule {
  ruleset: { id: string; version: string }
  module: string
  inputs: Record<string, unknown>
  results: Record<string, unknown>
  matched_rules: Array<{ id: string; name: string; source_id: string }>
  applied_rules: Array<{ id: string; name: string; source_id: string }>
  sources: NajiaSource[]
  explanation: string
}

export interface NajiaRuleAnalysis {
  ruleset: { id: string; version: string }
  enabled: Record<'use_god' | 'time_relations' | 'branch_relations' | 'moving_changes', boolean>
  question_category: string | null
  manual_use_god_candidate: string | null
  modules: Record<string, NajiaRuleModule | null>
}

export interface CalendarContext {
  ruleset_id: string
  ruleset_version: string
  engine: string
  engine_version: string
  timezone_database: string
  timezone_database_version: string
  local_datetime: string
  timezone: string
  utc_offset: string
  utc_instant: string
  day_ganzhi: string
  day_rule: string
  month_branch: string
  month_rule: string
  jieqi_reference_timezone: string
}

export interface NajiaOptions {
  day_ganzhi_options: string[]
  month_branches: string[]
}

export interface NajiaBoard {
  hexagram_order: number
  hexagram_title: string
  binary_code: string
  lines: NajiaLine[]
}

export interface AiSessionSummary {
  id: number
  mode: 'classical' | 'najia'
  model_id: string
  created_at: string
}

export interface AISettings {
  provider: 'deepseek'
  api_key_configured: boolean
  ai_enabled: boolean
  model_id: string | null
}

export interface AppPreferences {
  default_method: 'coins' | 'manual'
  timezone: string
  ai_default_mode: 'classical' | 'najia'
  ruleset_id: string
  ruleset_version: string
}

export interface NajiaAnalysisInput {
  enabled: Record<'use_god' | 'time_relations' | 'branch_relations' | 'moving_changes', boolean>
  question_category?: string | null
  manual_use_god_candidate?: string | null
}

export type NajiaInput = (
  | { source: 'manual'; day_ganzhi: string; month_branch: string }
  | { source: 'automatic'; local_datetime: string; timezone: string }
) & { analysis?: NajiaAnalysisInput }

export interface AIModel {
  id: string
  owned_by: string
}

export interface AIInterpretation {
  response_schema?: 'ai-response@2'
  overview: string
  cited_rule_ids?: string[]
  cited_rules?: Array<{
    id: string
    name: string
    source_id?: string
    source_title?: string
    source_url?: string
    source_revision_id?: number
    rule_scope?: string
  }>
  cited_passages: Array<{
    id: string
    label: string
    text: string
    source_url: string
    source_revision_id: number | null
  }>
  traditional_basis: string | Array<{
    evidence_id: string
    explanation: string
  }>
  modern_interpretation: string
  suggestions: string[]
  ruleset: { id: string; version: string; name: string }
  mode: 'classical' | 'najia'
  caution: string
  provider?: {
    model_id: string
    usage: { prompt_tokens: number; completion_tokens: number; cache_hit_tokens: number; cache_miss_tokens: number } | null
    cost_estimate: { currency: string; off_peak: number; peak: number } | null
    pricing_checked_at?: string | null
    pricing_source_url?: string | null
    note?: string
  }
}

export interface AISessionMessage {
  id: number
  role: 'user' | 'assistant'
  content: string | AIInterpretation
  created_at: string
  request_id?: string | null
  user_message_id?: number | null
}

export interface AIStreamResult {
  message: AISessionMessage
  user_message: AISessionMessage
}

export interface AIFailedRequest {
  request_id: string
  message_text: string
  regenerate_from_message_id: number | null
  code: string
  stage: string
  message: string
  created_at: string
}

export interface AISession {
  id: number
  divination_id: number
  mode: 'classical' | 'najia'
  model_id: string
  rule_versions?: Record<string, unknown>
  created_at: string
  messages: AISessionMessage[]
  failed_requests?: AIFailedRequest[]
}

export interface HistorySummary {
  id: number
  question: string
  method: 'coins' | 'manual'
  base_name: string
  changed_name: string
  moving_positions: number[]
  created_at: string
  has_ai_sessions?: boolean
}

export interface HistoryList {
  items: HistorySummary[]
  total: number
}

export type HistoryAIFilter = 'all' | 'with-ai' | 'without-ai'

export interface HistoryQuery {
  q?: string
  ai_filter?: HistoryAIFilter
  limit?: number
  offset?: number
}
