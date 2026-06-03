/**
 * constants.js — Shared constants for the extension
 *
 * Centralises message types, storage keys, and default settings.
 * Import this in background, popup, sidebar, and content scripts.
 */

// ---------------------------------------------------------------------------
// Message types (background.js router)
// ---------------------------------------------------------------------------
export const MESSAGES = Object.freeze({
  DRAFT_REPLY: 'DRAFT_REPLY',
  GENERATE_POST: 'GENERATE_POST',
  GET_TRENDS: 'GET_TRENDS',
  ANALYZE_POST: 'ANALYZE_POST',
  GET_SETTINGS: 'GET_SETTINGS',
  SAVE_SETTINGS: 'SAVE_SETTINGS',
  GET_DRAFTS: 'GET_DRAFTS',
  SAVE_DRAFT: 'SAVE_DRAFT',
  DELETE_DRAFT: 'DELETE_DRAFT',
  OPEN_SIDEBAR: 'OPEN_SIDEBAR',
  HEALTH_CHECK: 'HEALTH_CHECK',
  INJECT_TEXT: 'INJECT_TEXT',
  EXTRACT_POST: 'EXTRACT_POST',
  // New feature messages
  RECORD_AB_TEST: 'RECORD_AB_TEST',
  GET_AB_SUMMARY: 'GET_AB_SUMMARY',
  EXPORT_DRAFTS: 'EXPORT_DRAFTS',
  GET_CALENDAR: 'GET_CALENDAR',
  CREATE_CALENDAR_POST: 'CREATE_CALENDAR_POST',
  DELETE_CALENDAR_POST: 'DELETE_CALENDAR_POST',
  UPDATE_CALENDAR_POST: 'UPDATE_CALENDAR_POST',
  GET_STYLE_PROFILE: 'GET_STYLE_PROFILE',
  LEARN_STYLE: 'LEARN_STYLE',
  // Usage stats
  GET_USAGE_STATS: 'GET_USAGE_STATS',
  RESET_USAGE_STATS: 'RESET_USAGE_STATS',
  // Analytics
  GET_ANALYTICS: 'GET_ANALYTICS',
  STORE_ANALYTICS: 'STORE_ANALYTICS',
  // Growth optimizer
  GET_OPTIMAL_TIMES: 'GET_OPTIMAL_TIMES',
  OPTIMIZE_HASHTAGS: 'OPTIMIZE_HASHTAGS',
  GET_GROWTH_TIPS: 'GET_GROWTH_TIPS',
  // Algorithm score
  GET_ALGORITHM_SCORE: 'GET_ALGORITHM_SCORE',
  // Authority builder
  ANALYZE_AUTHORITY: 'ANALYZE_AUTHORITY',
  GET_ENGAGEMENT_SUGGESTIONS: 'GET_ENGAGEMENT_SUGGESTIONS',
  // Time tracking
  LOG_TIME_SESSION: 'LOG_TIME_SESSION',
  GET_TIME_SUMMARY: 'GET_TIME_SUMMARY',
  GET_LOCAL_TIME_DATA: 'GET_LOCAL_TIME_DATA',
  SAVE_TIME_GOAL: 'SAVE_TIME_GOAL',
});

// ---------------------------------------------------------------------------
// chrome.storage.local keys
// ---------------------------------------------------------------------------
export const STORAGE_KEYS = Object.freeze({
  SETTINGS: 'lea_settings',
  DRAFTS: 'lea_drafts',
  TRENDS_CACHE: 'lea_trends_cache',
  PERSONAS: 'lea_personas',
  POST_CACHE: 'lea_post_cache',
  USAGE_STATS: 'lea_usage_stats',
  ANALYTICS: 'lea_analytics',
  // Time tracking (extension-local — never sent to backend raw)
  TIME_SESSIONS: 'lea_time_sessions',   // {date: {active, idle, pageViews, actions, productive}}
  TIME_GOALS: 'lea_time_goals',         // {dailyMinutes, weeklyMinutes}
  // Authority cache
  AUTHORITY_CACHE: 'lea_authority_cache',
});

// ---------------------------------------------------------------------------
// Default settings
// ---------------------------------------------------------------------------
export const DEFAULT_SETTINGS = Object.freeze({
  backendUrl: 'http://localhost:8000',
  apiKey: '',
  llmProvider: 'openai',
  defaultTone: 'professional',
  defaultPersona: 'senior_engineer',
  sidebarEnabled: true,
  debugMode: false,
  autoOpenSidebar: false,
  privacyMode: false,  // When true: removes extension fingerprints from the DOM
});

// ---------------------------------------------------------------------------
// Tone options
// ---------------------------------------------------------------------------
export const TONES = Object.freeze([
  { value: 'professional', label: 'Professional' },
  { value: 'concise', label: 'Concise' },
  { value: 'expert', label: 'Expert Deep Dive' },
  { value: 'contrarian', label: 'Contrarian' },
  { value: 'founder', label: 'Founder Voice' },
  { value: 'recruiter', label: 'Recruiter Warm' },
]);

// ---------------------------------------------------------------------------
// Persona options
// ---------------------------------------------------------------------------
export const PERSONAS = Object.freeze([
  { value: 'senior_engineer', label: 'Senior Engineer' },
  { value: 'product_manager', label: 'Product Manager' },
  { value: 'executive', label: 'Executive' },
  { value: 'entrepreneur', label: 'Entrepreneur' },
  { value: 'researcher', label: 'Researcher' },
  { value: 'consultant', label: 'Consultant' },
]);

// ---------------------------------------------------------------------------
// Post styles
// ---------------------------------------------------------------------------
export const POST_STYLES = Object.freeze([
  { value: 'professional', label: 'Professional' },
  { value: 'educational', label: 'Educational' },
  { value: 'founder', label: 'Founder Story' },
  { value: 'technical', label: 'Technical Deep Dive' },
  { value: 'viral', label: 'Viral / Hook-First' },
  { value: 'concise_authority', label: 'Concise Authority' },
]);
