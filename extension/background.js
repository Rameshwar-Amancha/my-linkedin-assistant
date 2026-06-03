/**
 * background.js — Service Worker (classic script)
 *
 * Responsibilities:
 *  - Centralized message routing between content scripts, popup, and sidebar
 *  - API communication abstraction with retry logic
 *  - Auth token management (stored in chrome.storage.local only)
 *  - Extension lifecycle hooks
 *  - Storage synchronization helpers
 *
 * Security: API keys are NEVER forwarded to content scripts.
 * Content scripts send data payloads; background appends auth headers.
 *
 * NOTE: Constants are inlined here (not imported) so this file works as a
 * classic service worker script. popup.js / sidebar.js still import from
 * utils/constants.js via their own <script type="module"> tags.
 */

// ---------------------------------------------------------------------------
// Inlined constants (keep in sync with utils/constants.js)
// ---------------------------------------------------------------------------

const MESSAGES = Object.freeze({
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
  RECORD_AB_TEST: 'RECORD_AB_TEST',
  GET_AB_SUMMARY: 'GET_AB_SUMMARY',
  EXPORT_DRAFTS: 'EXPORT_DRAFTS',
  GET_CALENDAR: 'GET_CALENDAR',
  CREATE_CALENDAR_POST: 'CREATE_CALENDAR_POST',
  DELETE_CALENDAR_POST: 'DELETE_CALENDAR_POST',
  UPDATE_CALENDAR_POST: 'UPDATE_CALENDAR_POST',
  GET_STYLE_PROFILE: 'GET_STYLE_PROFILE',
  LEARN_STYLE: 'LEARN_STYLE',
  GET_USAGE_STATS: 'GET_USAGE_STATS',
  RESET_USAGE_STATS: 'RESET_USAGE_STATS',
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

const STORAGE_KEYS = Object.freeze({
  SETTINGS: 'lea_settings',
  DRAFTS: 'lea_drafts',
  TRENDS_CACHE: 'lea_trends_cache',
  PERSONAS: 'lea_personas',
  POST_CACHE: 'lea_post_cache',
  USAGE_STATS: 'lea_usage_stats',
  ANALYTICS: 'lea_analytics',
  TIME_SESSIONS: 'lea_time_sessions',
  TIME_GOALS: 'lea_time_goals',
  AUTHORITY_CACHE: 'lea_authority_cache',
});

const DEFAULT_SETTINGS = Object.freeze({
  backendUrl: 'http://localhost:8000',
  apiKey: '',
  llmProvider: 'openai',
  defaultTone: 'professional',
  defaultPersona: 'senior_engineer',
  sidebarEnabled: true,
  debugMode: false,
  autoOpenSidebar: false,
  privacyMode: false,
});

// ---------------------------------------------------------------------------
// Cross-browser compat (inlined — background.js is a classic SW, no imports)
// Firefox exposes `browser.*` globally; Chrome/Edge use `chrome.*` only.
// Most chrome.* APIs work on Firefox via the compat shim, except sidePanel.
// ---------------------------------------------------------------------------

const _isFirefox = typeof globalThis.browser !== 'undefined';
// chrome.sidePanel is Chrome/Edge 114+ only
const _hasSidePanel = typeof chrome.sidePanel !== 'undefined';

// ---------------------------------------------------------------------------
// Service worker lifecycle — explicit install/activate handlers
// These tell Chrome the install/activate phases complete immediately so that
// any fire-and-forget async work (e.g. updateBadge) doesn't accidentally
// race the SW registration state machine and produce status code 3.
// ---------------------------------------------------------------------------

self.addEventListener('install', (event) => {
  // Skip waiting so the new SW activates immediately on update
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  // Claim all clients immediately so content scripts use this SW right away
  event.waitUntil(self.clients.claim());
});

// ---------------------------------------------------------------------------
// Extension lifecycle
// ---------------------------------------------------------------------------

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === 'install') {
    initDefaultSettings();
    console.log('[LEA] Extension installed.');
  } else if (reason === 'update') {
    console.log('[LEA] Extension updated.');
    migrateSettings();
  }

  // Chrome/Edge: configure Side Panel behaviour on every install/update.
  // Keep the popup as the primary toolbar-click action; the side panel is
  // opened explicitly from the popup "Open Sidebar" button or keyboard shortcut.
  if (_hasSidePanel) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false }).catch(() => {});
  }
});

chrome.runtime.onStartup.addListener(() => {
  console.log('[LEA] Browser started — service worker active.');
});

// ---------------------------------------------------------------------------
// Keyboard shortcut handler
// ---------------------------------------------------------------------------

if (chrome.commands) {
  chrome.commands.onCommand.addListener((command, tab) => {
    if (command === 'open-sidebar') {
      const tabId = tab?.id;
      openSidebar(tabId).catch(() => {});
    }
  });
}

// ---------------------------------------------------------------------------
// Default settings initialisation
// ---------------------------------------------------------------------------

async function initDefaultSettings() {
  const existing = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  if (!existing[STORAGE_KEYS.SETTINGS]) {
    await chrome.storage.local.set({ [STORAGE_KEYS.SETTINGS]: DEFAULT_SETTINGS });
  }
}

async function migrateSettings() {
  // Future: apply settings migrations on extension update
  const data = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  const current = data[STORAGE_KEYS.SETTINGS] || {};
  const merged = Object.assign({}, DEFAULT_SETTINGS, current);
  await chrome.storage.local.set({ [STORAGE_KEYS.SETTINGS]: merged });
}

// ---------------------------------------------------------------------------
// Message router
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Validate message structure
  if (!message || typeof message.type !== 'string') {
    sendResponse({ success: false, error: 'Invalid message format' });
    return false;
  }

  // Route to appropriate handler (async)
  handleMessage(message, sender)
    .then(sendResponse)
    .catch((err) => {
      console.error('[LEA] Message handler error:', err);
      sendResponse({ success: false, error: err.message || 'Internal error' });
    });

  // Return true to keep the message channel open for async responses
  return true;
});

async function handleMessage(message, sender) {
  switch (message.type) {
    case MESSAGES.DRAFT_REPLY:
      return callBackendAPI('/api/draft-reply', 'POST', message.payload);

    case MESSAGES.GENERATE_POST:
      return callBackendAPI('/api/generate-post', 'POST', message.payload);

    case MESSAGES.GET_TRENDS:
      return callBackendAPI('/api/trends', 'GET', null, message.payload);

    case MESSAGES.ANALYZE_POST:
      return callBackendAPI('/api/analyze-post', 'POST', message.payload);

    case MESSAGES.GET_SETTINGS:
      return getSettings();

    case MESSAGES.SAVE_SETTINGS:
      return saveSettings(message.payload);

    case MESSAGES.GET_DRAFTS:
      return getDrafts();

    case MESSAGES.SAVE_DRAFT:
      return saveDraft(message.payload);

    case MESSAGES.DELETE_DRAFT:
      return deleteDraft(message.payload.id);

    case MESSAGES.OPEN_SIDEBAR:
      return openSidebar(message.payload?.tabId || sender.tab?.id);

    case MESSAGES.HEALTH_CHECK:
      return callBackendAPI('/api/health', 'GET');

    // A/B testing
    case MESSAGES.RECORD_AB_TEST:
      return callBackendAPI('/api/ab-test/record', 'POST', message.payload);

    case MESSAGES.GET_AB_SUMMARY:
      return callBackendAPI('/api/ab-test/summary', 'GET');

    // Export
    case MESSAGES.EXPORT_DRAFTS:
      return exportDraftsCSV();

    // Content calendar
    case MESSAGES.GET_CALENDAR:
      return callBackendAPI('/api/calendar', 'GET', null, message.payload);

    case MESSAGES.CREATE_CALENDAR_POST:
      return callBackendAPI('/api/calendar', 'POST', message.payload);

    case MESSAGES.DELETE_CALENDAR_POST:
      return callBackendAPI(`/api/calendar/${message.payload.id}`, 'DELETE');

    case MESSAGES.UPDATE_CALENDAR_POST:
      return callBackendAPI(`/api/calendar/${message.payload.id}`, 'PATCH', message.payload.updates);

    // Style profile
    case MESSAGES.GET_STYLE_PROFILE:
      return callBackendAPI('/api/style/profile', 'GET');

    case MESSAGES.LEARN_STYLE:
      return callBackendAPI('/api/style/learn', 'POST', message.payload);

    // Usage stats
    case MESSAGES.GET_USAGE_STATS:
      return getUsageStats();

    case MESSAGES.RESET_USAGE_STATS:
      return resetUsageStats();

    // Analytics (stored locally — extracted from LinkedIn's own analytics pages)
    case MESSAGES.GET_ANALYTICS:
      return getAnalytics();

    case MESSAGES.STORE_ANALYTICS:
      return storeAnalytics(message.payload);

    // Growth optimizer
    case MESSAGES.GET_OPTIMAL_TIMES:
      return callBackendAPI('/api/growth/optimal-times', 'GET');

    case MESSAGES.OPTIMIZE_HASHTAGS:
      return callBackendAPI('/api/growth/hashtag-optimize', 'POST', message.payload);

    case MESSAGES.GET_GROWTH_TIPS:
      return callBackendAPI('/api/growth/tips', 'GET');

    // Algorithm score
    case MESSAGES.GET_ALGORITHM_SCORE:
      return callBackendAPI('/api/algorithm/score', 'POST', message.payload);

    // Authority builder
    case MESSAGES.ANALYZE_AUTHORITY:
      return callBackendAPI('/api/authority/analyze', 'POST', message.payload);

    case MESSAGES.GET_ENGAGEMENT_SUGGESTIONS:
      return callBackendAPI('/api/authority/suggestions', 'GET', null, message.payload);

    // Time tracking
    case MESSAGES.LOG_TIME_SESSION:
      return logTimeSessionLocal(message.payload);

    case MESSAGES.GET_TIME_SUMMARY:
      return callBackendAPI('/api/time-tracking/summary', 'GET');

    case MESSAGES.GET_LOCAL_TIME_DATA:
      return getLocalTimeData();

    case MESSAGES.SAVE_TIME_GOAL:
      return saveTimeGoal(message.payload);

    default:
      return { success: false, error: `Unknown message type: ${message.type}` };
  }
}

// ---------------------------------------------------------------------------
// API client with retry and auth injection
// ---------------------------------------------------------------------------

const REQUEST_QUEUE = new Map(); // dedup in-flight requests

async function callBackendAPI(path, method = 'POST', body = null, queryParams = null, retries = 3) {
  const settings = await getSettings();
  const backendUrl = settings.backendUrl || 'http://localhost:8000';
  const apiKey = settings.apiKey || '';

  let url = `${backendUrl}${path}`;
  if (queryParams) {
    const params = new URLSearchParams(
      Object.entries(queryParams).filter(([, v]) => v !== null && v !== undefined)
    );
    if (params.toString()) url += `?${params}`;
  }

  // Dedup concurrent identical GET requests
  const dedupKey = method === 'GET' ? url : null;
  if (dedupKey && REQUEST_QUEUE.has(dedupKey)) {
    return REQUEST_QUEUE.get(dedupKey);
  }

  const requestPromise = executeRequest(url, method, body, apiKey, retries, path);

  if (dedupKey) {
    REQUEST_QUEUE.set(dedupKey, requestPromise);
    requestPromise.finally(() => REQUEST_QUEUE.delete(dedupKey));
  }

  return requestPromise;
}

// Map API paths to human-friendly action counter keys
const ACTION_KEY_MAP = {
  '/api/draft-reply':   { total: 'totalReplies',   today: 'todayReplies' },
  '/api/generate-post': { total: 'totalPosts',     today: 'todayPosts' },
  '/api/analyze-post':  { total: 'totalAnalyses',  today: 'todayAnalyses' },
  '/api/trends':        { total: 'totalTrends',    today: 'todayTrends' },
};

// Track token usage + optional per-action counter after each successful LLM call
async function trackUsage(tokensUsed, apiPath) {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const data = await chrome.storage.local.get(STORAGE_KEYS.USAGE_STATS);
  const stats = data[STORAGE_KEYS.USAGE_STATS] || {};

  const isNewDay = stats.lastResetDate !== today;

  const update = {
    totalRequests: (stats.totalRequests || 0) + 1,
    todayRequests: isNewDay ? 1 : (stats.todayRequests || 0) + 1,
    lastResetDate: today,
    updatedAt: Date.now(),
  };

  // Token tracking (only when the response carried a tokens_used field)
  if (tokensUsed && tokensUsed > 0) {
    update.totalTokens = (stats.totalTokens || 0) + tokensUsed;
    update.todayTokens = isNewDay ? tokensUsed : (stats.todayTokens || 0) + tokensUsed;
  } else {
    update.totalTokens = stats.totalTokens || 0;
    update.todayTokens = isNewDay ? 0 : (stats.todayTokens || 0);
  }

  // Per-action counter (e.g. replies, posts, analyses)
  if (apiPath && ACTION_KEY_MAP[apiPath]) {
    const keys = ACTION_KEY_MAP[apiPath];
    update[keys.total] = (stats[keys.total] || 0) + 1;
    update[keys.today] = isNewDay ? 1 : (stats[keys.today] || 0) + 1;
    // Preserve other action counters unchanged
    for (const [, k] of Object.entries(ACTION_KEY_MAP)) {
      if (k.total !== keys.total) {
        if (!(k.total in update)) update[k.total] = isNewDay ? 0 : (stats[k.total] || 0);
        if (!(k.today in update)) update[k.today] = isNewDay ? 0 : (stats[k.today] || 0);
      }
    }
  }

  await chrome.storage.local.set({ [STORAGE_KEYS.USAGE_STATS]: update });
}

async function executeRequest(url, method, body, apiKey, retries, apiPath) {
  const settings = await getSettings();
  const headers = {
    'Content-Type': 'application/json',
  };

  // Omit the extension version header in privacy mode — it's a fingerprint
  if (!settings.privacyMode) {
    headers['X-Extension-Version'] = chrome.runtime.getManifest().version;
  }

  // Only attach API key if configured — never expose raw key to logs
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const options = { method, headers };
  if (body && method !== 'GET' && method !== 'DELETE') {
    options.body = JSON.stringify(body);
  }

  let lastError;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30_000); // 30s timeout

      const response = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
        // FastAPI 422 detail is an array of validation error objects — format it into a readable string
        let detail = errorBody.detail;
        if (Array.isArray(detail)) {
          detail = detail
            .map((e) => {
              const field = Array.isArray(e.loc) ? e.loc.slice(1).join('.') : String(e.loc);
              return field ? `${field}: ${e.msg}` : e.msg;
            })
            .join('; ');
        }
        throw new APIError(response.status, detail || 'API error');
      }

      const data = await response.json();
      // Track token consumption + action counter for LLM endpoints
      trackUsage(data?.tokens_used || 0, apiPath).catch(() => {});
      return { success: true, data };
    } catch (err) {
      lastError = err;

      if (err instanceof APIError && err.status < 500) {
        // Client errors (4xx) are not retried
        return { success: false, error: err.message, status: err.status };
      }

      if (err.name === 'AbortError') {
        return { success: false, error: 'Request timed out after 30s', status: 408 };
      }

      if (attempt < retries) {
        const delay = Math.min(1000 * 2 ** (attempt - 1), 8000); // exponential backoff
        console.warn(`[LEA] API call failed (attempt ${attempt}/${retries}), retrying in ${delay}ms...`);
        await sleep(delay);
      }
    }
  }

  return { success: false, error: lastError?.message || 'Network error after retries' };
}

class APIError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = 'APIError';
  }
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

async function getSettings() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  return Object.assign({}, DEFAULT_SETTINGS, data[STORAGE_KEYS.SETTINGS] || {});
}

async function saveSettings(updates) {
  const current = await getSettings();
  const merged = Object.assign({}, current, updates);

  // Validate critical fields
  if (merged.backendUrl && !isValidUrl(merged.backendUrl)) {
    return { success: false, error: 'Invalid backend URL' };
  }

  await chrome.storage.local.set({ [STORAGE_KEYS.SETTINGS]: merged });
  return { success: true };
}

async function getDrafts() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.DRAFTS);
  return { success: true, data: data[STORAGE_KEYS.DRAFTS] || [] };
}

async function saveDraft(draft) {
  if (!draft || typeof draft.content !== 'string') {
    return { success: false, error: 'Invalid draft payload' };
  }

  const data = await chrome.storage.local.get(STORAGE_KEYS.DRAFTS);
  const drafts = data[STORAGE_KEYS.DRAFTS] || [];

  const newDraft = {
    id: crypto.randomUUID(),
    content: draft.content.slice(0, 5000), // cap at 5KB
    label: (draft.label || 'Draft').slice(0, 100),
    tone: draft.tone || 'professional',
    createdAt: Date.now(),
    postContext: draft.postContext || null,
  };

  drafts.unshift(newDraft);

  // Keep only the 50 most recent drafts
  const trimmed = drafts.slice(0, 50);
  await chrome.storage.local.set({ [STORAGE_KEYS.DRAFTS]: trimmed });
  return { success: true, data: newDraft };
}

async function deleteDraft(id) {
  if (!id) return { success: false, error: 'Missing draft id' };
  const data = await chrome.storage.local.get(STORAGE_KEYS.DRAFTS);
  const drafts = (data[STORAGE_KEYS.DRAFTS] || []).filter((d) => d.id !== id);
  await chrome.storage.local.set({ [STORAGE_KEYS.DRAFTS]: drafts });
  return { success: true };
}

// ---------------------------------------------------------------------------
// Usage stats helpers
// ---------------------------------------------------------------------------

async function getUsageStats() {
  const settings = await getSettings();
  const data = await chrome.storage.local.get(STORAGE_KEYS.USAGE_STATS);
  const stats = data[STORAGE_KEYS.USAGE_STATS] || {};

  const providerModelMap = {
    openai: 'OpenAI gpt-4o',
    gemini: 'Gemini 1.5 Pro',
    anthropic: 'Claude 3.5 Sonnet',
  };

  return {
    success: true,
    data: {
      provider: settings.llmProvider || 'openai',
      providerLabel: providerModelMap[settings.llmProvider] || settings.llmProvider || 'OpenAI gpt-4o',
      // Tokens
      totalTokens:   stats.totalTokens   || 0,
      todayTokens:   stats.todayTokens   || 0,
      // Requests (all actions combined)
      totalRequests: stats.totalRequests || 0,
      todayRequests: stats.todayRequests || 0,
      // Per-action counts
      totalReplies:  stats.totalReplies  || 0,
      todayReplies:  stats.todayReplies  || 0,
      totalPosts:    stats.totalPosts    || 0,
      todayPosts:    stats.todayPosts    || 0,
      totalAnalyses: stats.totalAnalyses || 0,
      todayAnalyses: stats.todayAnalyses || 0,
      totalTrends:   stats.totalTrends   || 0,
      // Meta
      lastResetDate: stats.lastResetDate || null,
      updatedAt:     stats.updatedAt     || null,
    },
  };
}

async function resetUsageStats() {
  await chrome.storage.local.remove(STORAGE_KEYS.USAGE_STATS);
  return { success: true };
}

// ---------------------------------------------------------------------------
// Analytics helpers (stored locally from LinkedIn DOM extraction)
// ---------------------------------------------------------------------------

async function getAnalytics() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.ANALYTICS);
  return { success: true, data: data[STORAGE_KEYS.ANALYTICS] || [] };
}

async function storeAnalytics(payload) {
  if (!payload || typeof payload !== 'object') {
    return { success: false, error: 'Invalid analytics payload' };
  }

  const data = await chrome.storage.local.get(STORAGE_KEYS.ANALYTICS);
  const existing = data[STORAGE_KEYS.ANALYTICS] || [];

  // Deduplicate by postUrl — update if same post, otherwise prepend
  const idx = existing.findIndex((a) => a.postUrl && a.postUrl === payload.postUrl);
  if (idx >= 0) {
    existing[idx] = { ...existing[idx], ...payload, updatedAt: Date.now() };
  } else {
    existing.unshift({ ...payload, capturedAt: Date.now() });
  }

  // Keep the 100 most recent analytics snapshots
  const trimmed = existing.slice(0, 100);
  await chrome.storage.local.set({ [STORAGE_KEYS.ANALYTICS]: trimmed });
  return { success: true };
}

// ---------------------------------------------------------------------------
// Export helper — triggers CSV download via a backend call
// ---------------------------------------------------------------------------

async function exportDraftsCSV() {
  const settings = await getSettings();
  const backendUrl = settings.backendUrl || 'http://localhost:8000';
  const apiKey = settings.apiKey || '';

  if (!apiKey) {
    return { success: false, error: 'API key not configured.' };
  }

  try {
    // Fetch with auth header — never expose the key in a URL
    const response = await fetch(`${backendUrl}/api/export/drafts`, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey,
        'X-Extension-Version': chrome.runtime.getManifest().version,
      },
    });

    if (!response.ok) {
      return { success: false, error: `Export failed: ${response.status} ${response.statusText}` };
    }

    const csvText = await response.text();
    const tag = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    // Return as data URI so the sidebar can trigger a file download without
    // needing the "downloads" permission or exposing the key in a URL.
    const dataUri = `data:text/csv;charset=utf-8,${encodeURIComponent(csvText)}`;
    return { success: true, data: { dataUri, filename: `lea_drafts_${tag}.csv` } };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// ---------------------------------------------------------------------------
// Time Tracking helpers (local aggregation + backend sync)
// ---------------------------------------------------------------------------

async function logTimeSessionLocal(sessionData) {
  if (!sessionData || typeof sessionData.session_date !== 'string') {
    return { success: false, error: 'Invalid session data' };
  }

  // 1. Store locally in extension storage (source of truth for 30-day history)
  const data = await chrome.storage.local.get(STORAGE_KEYS.TIME_SESSIONS);
  const sessions = data[STORAGE_KEYS.TIME_SESSIONS] || {};
  const date = sessionData.session_date;

  const existing = sessions[date] || {
    active_seconds: 0,
    idle_seconds: 0,
    page_views: 0,
    actions_taken: 0,
    productive_seconds: 0,
  };

  sessions[date] = {
    active_seconds: existing.active_seconds + (sessionData.active_seconds || 0),
    idle_seconds: existing.idle_seconds + (sessionData.idle_seconds || 0),
    page_views: existing.page_views + (sessionData.page_views || 0),
    actions_taken: existing.actions_taken + (sessionData.actions_taken || 0),
    productive_seconds: existing.productive_seconds + (sessionData.productive_seconds || 0),
  };

  // Keep only 30 days of history to limit storage usage
  const sortedDates = Object.keys(sessions).sort().reverse().slice(0, 30);
  const trimmed = {};
  sortedDates.forEach((d) => { trimmed[d] = sessions[d]; });

  await chrome.storage.local.set({ [STORAGE_KEYS.TIME_SESSIONS]: trimmed });

  // 2. Sync to backend (non-blocking — failure is silent since local data is authoritative)
  callBackendAPI('/api/time-tracking/log', 'POST', sessionData).catch(() => {});

  return { success: true };
}

async function getLocalTimeData() {
  const [sessionsData, goalsData] = await Promise.all([
    chrome.storage.local.get(STORAGE_KEYS.TIME_SESSIONS),
    chrome.storage.local.get(STORAGE_KEYS.TIME_GOALS),
  ]);

  const sessions = sessionsData[STORAGE_KEYS.TIME_SESSIONS] || {};
  const goals = goalsData[STORAGE_KEYS.TIME_GOALS] || { dailyMinutes: 30, weeklyMinutes: 150 };

  // Compute quick stats from local data
  const today = new Date().toISOString().slice(0, 10);
  const todayData = sessions[today] || {};
  const todayActiveMin = Math.round((todayData.active_seconds || 0) / 60);
  const todayProductiveMin = Math.round((todayData.productive_seconds || 0) / 60);

  // 7-day breakdown
  const breakdown = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    const s = sessions[dateStr] || {};
    breakdown.push({
      date: dateStr,
      active_minutes: Math.round((s.active_seconds || 0) / 60),
      productive_minutes: Math.round((s.productive_seconds || 0) / 60),
      page_views: s.page_views || 0,
      actions_taken: s.actions_taken || 0,
    });
  }

  const weekActiveMin = breakdown.reduce((sum, d) => sum + d.active_minutes, 0);
  const weekProductiveMin = breakdown.reduce((sum, d) => sum + d.productive_minutes, 0);

  return {
    success: true,
    data: {
      today_active_minutes: todayActiveMin,
      today_productive_minutes: todayProductiveMin,
      week_active_minutes: weekActiveMin,
      week_productive_minutes: weekProductiveMin,
      daily_breakdown: breakdown,
      goals,
      focus_ratio: weekActiveMin > 0 ? Math.round((weekProductiveMin / weekActiveMin) * 100) : 0,
    },
  };
}

async function saveTimeGoal(goals) {
  if (!goals || typeof goals !== 'object') {
    return { success: false, error: 'Invalid goals payload' };
  }
  const sanitized = {
    dailyMinutes: Math.max(1, Math.min(480, parseInt(goals.dailyMinutes) || 30)),
    weeklyMinutes: Math.max(1, Math.min(3360, parseInt(goals.weeklyMinutes) || 150)),
  };
  await chrome.storage.local.set({ [STORAGE_KEYS.TIME_GOALS]: sanitized });
  return { success: true, data: sanitized };
}

// ---------------------------------------------------------------------------
// Sidebar management
// ---------------------------------------------------------------------------

async function openSidebar(tabId) {
  // Chrome / Edge — Side Panel API (Chrome 114+)
  if (_hasSidePanel) {
    if (!tabId) return { success: false, error: 'No active tab' };
    try {
      await chrome.sidePanel.open({ tabId });
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }

  // Firefox — sidebar_action API (browser.* namespace)
  if (_isFirefox && globalThis.browser?.sidebarAction) {
    try {
      await globalThis.browser.sidebarAction.open();
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }

  return { success: false, error: 'Sidebar API not available in this browser.' };
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isValidUrl(str) {
  try {
    const url = new URL(str);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Badge indicator for backend connectivity
// ---------------------------------------------------------------------------

async function updateBadge() {
  if (!chrome.action) return; // not available in all contexts
  try {
    const result = await callBackendAPI('/api/health', 'GET', null, null, 1);
    if (result.success) {
      await chrome.action.setBadgeText({ text: '' });
      await chrome.action.setBadgeBackgroundColor({ color: '#0A66C2' });
    } else {
      await chrome.action.setBadgeText({ text: '!' });
      await chrome.action.setBadgeBackgroundColor({ color: '#CC0000' });
    }
  } catch {
    try { await chrome.action.setBadgeText({ text: '?' }); } catch { /* ignore */ }
  }
}

// Run once each time the service worker wakes (install, update, message-triggered restart).
// Wrapped in a no-op catch so an unexpected rejection never causes a status-code-3 crash.
updateBadge().catch(() => {});
