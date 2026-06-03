/**
 * types.ts — TypeScript interfaces mirroring backend Pydantic schemas
 *
 * These are the canonical API contract types shared between the extension
 * and any TypeScript tooling (tests, type-checking, docs generation).
 *
 * Source of truth: shared/api-contracts/openapi.yaml
 */

// ─── Common ─────────────────────────────────────────────────────────────────

export interface ErrorResponse {
  detail: string;
  request_id?: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  llm_provider?: string;
}

// ─── Enums ───────────────────────────────────────────────────────────────────

export type Tone =
  | "professional"
  | "concise"
  | "expert"
  | "contrarian"
  | "founder"
  | "recruiter"
  | "thoughtful_question";

export type Persona =
  | "senior_engineer"
  | "product_manager"
  | "executive"
  | "entrepreneur"
  | "researcher"
  | "consultant";

export type PostStyle =
  | "professional"
  | "educational"
  | "founder"
  | "technical"
  | "viral"
  | "concise_authority";

export type AnalysisMode = "full" | "quick" | "summarize";

export type TrendCategory = "tech" | "ai" | "business" | "leadership" | "startups";

// ─── Draft Reply ──────────────────────────────────────────────────────────────

export interface DraftReplyRequest {
  author_name?: string;
  author_role?: string;
  /** Required. 10–5000 chars */
  post_content: string;
  media_context?: string;
  tone: Tone;
  persona: Persona;
  comment_context?: string;
}

export interface DraftReplyResponse {
  reply: string;
  reasoning: string;
  /** 0–10 engagement quality score */
  engagement_score: number;
  tone_used: Tone;
  tokens_used: number;
}

// ─── Generate Post ────────────────────────────────────────────────────────────

export interface GeneratePostRequest {
  /** Required. 10–1000 chars */
  topic: string;
  style: PostStyle;
  persona: Persona;
  /** 1–5. Default 3 */
  variations?: number;
  include_cta?: boolean;
  include_hashtags?: boolean;
  storytelling_mode?: boolean;
  additional_context?: string;
}

export interface PostVariation {
  content: string;
  hashtags: string[];
  /** 0–10 engagement prediction */
  engagement_prediction: number;
  word_count: number;
}

export interface GeneratePostResponse {
  variations: PostVariation[];
  topic_analyzed: string;
  tokens_used: number;
}

// ─── Analyze Post ────────────────────────────────────────────────────────────

export interface AnalyzePostRequest {
  /** Required. 20–5000 chars */
  content: string;
  mode?: AnalysisMode;
}

export interface PostScores {
  hook_strength: number;     // 0–10
  readability: number;       // 0–10
  authority_signals: number; // 0–10
  emotional_triggers: number; // 0–10
  cta_effectiveness: number; // 0–10
  overall: number;           // 0–10
}

export interface AnalyzePostResponse {
  scores: PostScores;
  recommendations: string[];
  summary: string;
  tokens_used: number;
}

// ─── Trends ──────────────────────────────────────────────────────────────────

export interface TrendItem {
  topic: string;
  source: string;
  url: string;
  /** 0–10 estimated LinkedIn engagement potential */
  engagement_potential: number;
  suggested_angle: string;
  published_at: string;
}

// ─── Settings (extension-side) ───────────────────────────────────────────────

export interface LEASettings {
  backendUrl: string;
  apiKey: string;
  llmProvider: "openai" | "gemini" | "anthropic";
  defaultTone: Tone;
  defaultPersona: Persona;
  autoOpenSidebar: boolean;
  showButtonsOnFeed: boolean;
}

// ─── Algorithm Score ─────────────────────────────────────────────────────────

export interface AlgorithmScoreRequest {
  /** Required. 20–5000 chars */
  content: string;
  has_media?: boolean;
  /** 0–23 */
  scheduled_hour?: number;
  scheduled_day?: "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";
}

export interface AlgorithmScoreResponse {
  /** 0–10 overall algorithm distribution score */
  algorithm_score: number;
  /** "local" | "broad" | "viral" */
  distribution_tier: string;
  /** 0–10 first-line hook effectiveness */
  hook_score: number;
  /** 0–10 share/save potential */
  virality_score: number;
  word_count: number;
  hashtag_count: number;
  /** 0–10 posting time quality */
  timing_score: number;
  suggestions: string[];
  first_comment_tip: string;
  tokens_used: number;
}

// ─── Growth Optimizer ────────────────────────────────────────────────────────

export interface HashtagOptimizeRequest {
  topic: string;
  persona?: Persona;
  target_audience?: string;
}

export interface HashtagSuggestion {
  hashtag: string;
  estimated_reach: "niche" | "medium" | "broad";
  engagement_level: "low" | "medium" | "high";
  reason: string;
}

export interface HashtagOptimizeResponse {
  primary_hashtags: HashtagSuggestion[];
  secondary_hashtags: HashtagSuggestion[];
  avoid_hashtags: string[];
  recommended_count: number;
  tokens_used: number;
}

export interface OptimalTimingResponse {
  best_days: string[];
  best_hours: number[];
  timezone_note: string;
  heatmap: Record<string, number[]>;
  reasoning: string;
}

export interface GrowthTip {
  category: "content" | "engagement" | "profile" | "consistency" | "network";
  tip: string;
  impact: "high" | "medium" | "low";
  action: string;
}

export interface GrowthTipsResponse {
  tips: GrowthTip[];
  weekly_focus: string;
  follower_growth_levers: string[];
}

// ─── Authority Builder ───────────────────────────────────────────────────────

export interface AuthorityAnalyzeRequest {
  post_samples: string[];
  professional_context?: string;
}

export interface CredibilitySignals {
  uses_data_stats: boolean;
  uses_personal_stories: boolean;
  uses_specific_examples: boolean;
  uses_frameworks: boolean;
  has_contrarian_views: boolean;
  mentions_credentials: boolean;
}

export interface AuthorityAnalyzeResponse {
  /** 0–10 thought leadership score */
  authority_score: number;
  topic_expertise: string[];
  engagement_tips: string[];
  credibility_signals: CredibilitySignals;
  authority_summary: string;
  growth_actions: string[];
  tokens_used: number;
}

export interface EngagementSuggestionsResponse {
  topics_to_comment_on: string[];
  posting_cadence: string;
  engagement_strategy: string;
  comment_templates: string[];
  authority_building_content: string[];
}

// ─── Time Tracking ───────────────────────────────────────────────────────────

export interface TimeSessionLog {
  /** YYYY-MM-DD */
  session_date: string;
  active_seconds: number;
  idle_seconds: number;
  page_views: number;
  actions_taken: number;
  productive_seconds: number;
}

export interface TimeTrackingDailyEntry {
  date: string;
  active_minutes: number;
  productive_minutes: number;
  page_views: number;
  actions_taken: number;
}

export interface TimeTrackingSummaryResponse {
  today_active_minutes: number;
  today_productive_minutes: number;
  week_active_minutes: number;
  week_productive_minutes: number;
  daily_breakdown: TimeTrackingDailyEntry[];
  insights: string[];
  /** 0.0–1.0 */
  focus_ratio: number;
}

export interface TimeGoals {
  dailyMinutes: number;
  weeklyMinutes: number;
}
