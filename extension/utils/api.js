/**
 * api.js — Extension API client (for popup/sidebar use)
 *
 * Sends messages to background.js which handles actual HTTP calls.
 * Content scripts use a different path (they cannot import ES modules).
 */

import { MESSAGES } from './constants.js';
import { ext, openExtensionSidebar } from './browser.js';

const DEFAULT_BACKEND_URL = 'http://localhost:8000';

/**
 * Send a typed message to background.js and await response.
 * Uses the browser-native Promise API (Firefox: `browser.*`, Chrome/Edge: `chrome.*`).
 * @param {string} type - MESSAGES constant
 * @param {object} payload
 * @returns {Promise<{success: boolean, data?: any, error?: string}>}
 */
async function sendMessage(type, payload = {}) {
  return ext.runtime.sendMessage({ type, payload });
}

// ---------------------------------------------------------------------------
// Public API methods
// ---------------------------------------------------------------------------

export async function draftReply(params) {
  return sendMessage(MESSAGES.DRAFT_REPLY, params);
}

export async function generatePost(params) {
  return sendMessage(MESSAGES.GENERATE_POST, params);
}

export async function getTrends(params = {}) {
  return sendMessage(MESSAGES.GET_TRENDS, params);
}

export async function analyzePost(params) {
  return sendMessage(MESSAGES.ANALYZE_POST, params);
}

export async function getSettings() {
  return sendMessage(MESSAGES.GET_SETTINGS);
}

export async function saveSettings(updates) {
  return sendMessage(MESSAGES.SAVE_SETTINGS, updates);
}

export async function getDrafts() {
  return sendMessage(MESSAGES.GET_DRAFTS);
}

export async function saveDraft(draft) {
  return sendMessage(MESSAGES.SAVE_DRAFT, draft);
}

export async function deleteDraft(id) {
  return sendMessage(MESSAGES.DELETE_DRAFT, { id });
}

export async function openSidebar() {
  // Get the active tab id and pass it to the browser-specific sidebar opener
  const tabs = await ext.tabs.query({ active: true, currentWindow: true });
  const tabId = tabs[0]?.id;
  return sendMessage(MESSAGES.OPEN_SIDEBAR, { tabId });
}

export async function healthCheck() {
  return sendMessage(MESSAGES.HEALTH_CHECK);
}

// ---------------------------------------------------------------------------
// A/B Testing
// ---------------------------------------------------------------------------

export async function recordABTest(params) {
  return sendMessage(MESSAGES.RECORD_AB_TEST, params);
}

export async function getABSummary() {
  return sendMessage(MESSAGES.GET_AB_SUMMARY);
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export async function exportDrafts() {
  return sendMessage(MESSAGES.EXPORT_DRAFTS);
}

// ---------------------------------------------------------------------------
// Content Calendar
// ---------------------------------------------------------------------------

export async function getCalendar(params = {}) {
  return sendMessage(MESSAGES.GET_CALENDAR, params);
}

export async function createCalendarPost(post) {
  return sendMessage(MESSAGES.CREATE_CALENDAR_POST, post);
}

export async function updateCalendarPost(id, updates) {
  return sendMessage(MESSAGES.UPDATE_CALENDAR_POST, { id, updates });
}

export async function deleteCalendarPost(id) {
  return sendMessage(MESSAGES.DELETE_CALENDAR_POST, { id });
}

// ---------------------------------------------------------------------------
// Personal Writing Style
// ---------------------------------------------------------------------------

export async function getStyleProfile() {
  return sendMessage(MESSAGES.GET_STYLE_PROFILE);
}

export async function learnStyle(draftSamples) {
  return sendMessage(MESSAGES.LEARN_STYLE, { draft_samples: draftSamples });
}

// ---------------------------------------------------------------------------
// Usage stats
// ---------------------------------------------------------------------------

export async function getUsageStats() {
  return sendMessage(MESSAGES.GET_USAGE_STATS);
}

export async function resetUsageStats() {
  return sendMessage(MESSAGES.RESET_USAGE_STATS);
}

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export async function getAnalytics() {
  return sendMessage(MESSAGES.GET_ANALYTICS);
}

export async function storeAnalytics(data) {
  return sendMessage(MESSAGES.STORE_ANALYTICS, data);
}

// ---------------------------------------------------------------------------
// Growth Optimizer
// ---------------------------------------------------------------------------

export async function getOptimalTimes() {
  return sendMessage(MESSAGES.GET_OPTIMAL_TIMES);
}

export async function optimizeHashtags(params) {
  return sendMessage(MESSAGES.OPTIMIZE_HASHTAGS, params);
}

export async function getGrowthTips() {
  return sendMessage(MESSAGES.GET_GROWTH_TIPS);
}

// ---------------------------------------------------------------------------
// Algorithm Score
// ---------------------------------------------------------------------------

export async function getAlgorithmScore(params) {
  return sendMessage(MESSAGES.GET_ALGORITHM_SCORE, params);
}

// ---------------------------------------------------------------------------
// Authority Builder
// ---------------------------------------------------------------------------

export async function analyzeAuthority(params) {
  return sendMessage(MESSAGES.ANALYZE_AUTHORITY, params);
}

export async function getEngagementSuggestions(params = {}) {
  return sendMessage(MESSAGES.GET_ENGAGEMENT_SUGGESTIONS, params);
}

// ---------------------------------------------------------------------------
// Time Tracking
// ---------------------------------------------------------------------------

export async function logTimeSession(sessionData) {
  return sendMessage(MESSAGES.LOG_TIME_SESSION, sessionData);
}

export async function getTimeSummary() {
  return sendMessage(MESSAGES.GET_TIME_SUMMARY);
}

export async function getLocalTimeData() {
  return sendMessage(MESSAGES.GET_LOCAL_TIME_DATA);
}

export async function saveTimeGoal(goals) {
  return sendMessage(MESSAGES.SAVE_TIME_GOAL, goals);
}
