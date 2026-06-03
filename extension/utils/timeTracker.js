/**
 * timeTracker.js — LinkedIn time tracking utility (content script module)
 *
 * Tracks active vs idle time while the user is on LinkedIn pages.
 * Reports sessions to the background service worker which aggregates
 * and optionally syncs to the backend.
 *
 * Privacy: Only total seconds are tracked — no URLs, scroll position,
 * or page content is recorded. All data is stored locally first.
 *
 * Activity detection: mouse moves, clicks, keyboard input, scroll.
 * Idle threshold: 60 seconds of no activity → stops counting active time.
 */

const IDLE_THRESHOLD_MS = 60_000;  // 60 seconds
const REPORT_INTERVAL_MS = 5 * 60_000;  // Report every 5 minutes
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];

let _activeSeconds = 0;
let _idleSeconds = 0;
let _pageViews = 1;         // Count this page load
let _actionsTaken = 0;      // AI assists used this session
let _productiveSeconds = 0; // Time spent using AI tools

let _lastActivityTime = Date.now();
let _sessionStart = Date.now();
let _isActive = true;
let _tickInterval = null;
let _reportInterval = null;
let _isTracking = false;

/**
 * Start the time tracker. Call once when content script initializes.
 */
export function startTracking() {
  if (_isTracking) return;
  _isTracking = true;
  _sessionStart = Date.now();
  _lastActivityTime = Date.now();

  // Register activity listeners
  ACTIVITY_EVENTS.forEach((evt) => {
    document.addEventListener(evt, _onActivity, { passive: true });
  });

  // Tick every second — classify as active or idle
  _tickInterval = setInterval(_tick, 1000);

  // Report to background every 5 minutes
  _reportInterval = setInterval(_reportSession, REPORT_INTERVAL_MS);

  // Report when tab is closed / navigated away
  window.addEventListener('beforeunload', _onUnload, { once: true });
  document.addEventListener('visibilitychange', _onVisibilityChange);
}

/**
 * Stop tracking and do a final report.
 */
export function stopTracking() {
  if (!_isTracking) return;
  _isTracking = false;

  ACTIVITY_EVENTS.forEach((evt) => {
    document.removeEventListener(evt, _onActivity);
  });

  clearInterval(_tickInterval);
  clearInterval(_reportInterval);
  document.removeEventListener('visibilitychange', _onVisibilityChange);

  _reportSession();
}

/**
 * Record that an AI action was taken (called by content.js).
 * @param {number} [productiveSecs=30] - Estimated productive seconds for this action
 */
export function recordAIAction(productiveSecs = 30) {
  _actionsTaken++;
  _productiveSeconds += productiveSecs;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function _onActivity() {
  _lastActivityTime = Date.now();
  _isActive = true;
}

function _tick() {
  const now = Date.now();
  const idleMs = now - _lastActivityTime;

  if (document.hidden) {
    // Tab not visible — count as idle
    _idleSeconds++;
    _isActive = false;
  } else if (idleMs > IDLE_THRESHOLD_MS) {
    _idleSeconds++;
    _isActive = false;
  } else {
    _activeSeconds++;
    _isActive = true;
  }
}

function _onVisibilityChange() {
  if (!document.hidden) {
    // Tab became visible again — reset last activity
    _lastActivityTime = Date.now();
  }
}

async function _reportSession() {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

  if (_activeSeconds === 0 && _idleSeconds === 0) return;

  const sessionData = {
    session_date: today,
    active_seconds: _activeSeconds,
    idle_seconds: _idleSeconds,
    page_views: _pageViews,
    actions_taken: _actionsTaken,
    productive_seconds: _productiveSeconds,
  };

  // Reset counters (don't double-count on next report)
  _activeSeconds = 0;
  _idleSeconds = 0;
  _pageViews = 0;
  _actionsTaken = 0;
  _productiveSeconds = 0;

  try {
    // Send to background for local storage + optional backend sync
    await chrome.runtime.sendMessage({ type: 'LOG_TIME_SESSION', payload: sessionData });
  } catch (_) {
    // Service worker may have been terminated — restore counters for next tick
    _activeSeconds += sessionData.active_seconds;
    _idleSeconds += sessionData.idle_seconds;
  }
}

function _onUnload() {
  // Synchronous-ish final flush using sendBeacon if possible, else sendMessage
  _reportSession();
}

/**
 * Get current in-memory stats (for display without waiting for next report).
 */
export function getCurrentStats() {
  return {
    activeSeconds: _activeSeconds,
    idleSeconds: _idleSeconds,
    isActive: _isActive,
    sessionDurationSeconds: Math.round((Date.now() - _sessionStart) / 1000),
  };
}
