/**
 * content.js — Main content script entry point
 *
 * Orchestrates:
 *  1. Feed observation via MutationObserver (SPA-aware)
 *  2. Post button injection (idempotent)
 *  3. AI action handling (draft reply, summarize, contrarian, question)
 *  4. Communication with background.js via chrome.runtime.sendMessage
 *
 * Architecture: Uses the global window.LEA namespace populated by
 * extractor.js and injector.js which are loaded before this file
 * via manifest.json content_scripts ordering.
 *
 * IMPORTANT: This script NEVER auto-posts, auto-likes, or auto-connects.
 * All actions require explicit user interaction.
 */

(function () {
  'use strict';

  // Guard against double-injection (e.g. if LinkedIn reloads scripts)
  if (window.__LEA_CONTENT_LOADED__) return;
  // Keep the guard flag under a low-risk name; we'll remove it after init
  window.__LEA_CONTENT_LOADED__ = true;

  // ---------------------------------------------------------------------------
  // Configuration
  // ---------------------------------------------------------------------------

  const SELECTORS = {
    POST_CONTAINER: [
      '.feed-shared-update-v2',
      '[data-urn*="activity"]',
      '.occludable-update',
    ].join(', '),
    FEED_ROOT: [
      '.scaffold-finite-scroll__content',
      '#main .feed-new-update-pill-container + div',
      '.core-rail',
      'main',
    ].join(', '),
  };

  // Use a WeakSet instead of a DOM attribute to track processed posts.
  // A DOM attribute (data-lea-processed) is a detectable fingerprint that
  // third-party scripts or LinkedIn's own code could use to identify the
  // extension. WeakSet keeps the tracking entirely in JS memory.
  const _processedPosts = new WeakSet();

  const DEBOUNCE_MS = 500;
  const MAX_POSTS_PER_SCAN = 20;

  // ---------------------------------------------------------------------------
  // Debounce utility (no external import in content scripts)
  // ---------------------------------------------------------------------------

  function debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  // ---------------------------------------------------------------------------
  // Post processing
  // ---------------------------------------------------------------------------

  function processPosts() {
    const posts = document.querySelectorAll(SELECTORS.POST_CONTAINER);
    let processed = 0;

    posts.forEach((post) => {
      if (processed >= MAX_POSTS_PER_SCAN) return;
      if (_processedPosts.has(post)) return;
      if (!isValidPost(post)) return;

      _processedPosts.add(post);
      injectPostButtons(post);
      processed++;
    });
  }

  function isValidPost(postEl) {
    // Skip sponsored posts and ads
    const isSponsored =
      postEl.querySelector('[aria-label*="Promoted"]') ||
      postEl.querySelector('[data-test-id="social-actions-bar"] span')?.textContent?.includes('Promoted') ||
      postEl.querySelector('.feed-shared-actor__sub-description')?.textContent?.includes('Promoted');

    if (isSponsored) return false;

    // Ensure post has some text content
    const hasContent =
      postEl.querySelector('.feed-shared-update-v2__description') ||
      postEl.querySelector('.update-components-text');

    return Boolean(hasContent);
  }

  // ---------------------------------------------------------------------------
  // Button injection and action handling
  // ---------------------------------------------------------------------------

  function injectPostButtons(postEl) {
    if (!window.LEA?.injectPostButtons) return;

    window.LEA.injectPostButtons(postEl, async (action, postData, triggerBtn) => {
      await handleAction(action, postData, postEl, triggerBtn);
    });
  }

  async function handleAction(action, postData, postEl, triggerBtn) {
    if (!postData) {
      window.LEA?.showToast('Could not extract post data. Please try again.', 'error');
      return;
    }

    window.LEA?.setButtonLoading(triggerBtn, true);

    try {
      const settings = await getSettings();
      const tone = settings.defaultTone || 'professional';
      const persona = settings.defaultPersona || 'senior_engineer';

      switch (action) {
        case 'draft_reply':
          await handleDraftReply(postData, tone, persona, postEl);
          break;
        case 'summarize':
          await handleSummarize(postData, postEl);
          break;
        case 'contrarian':
          await handleContrarian(postData, postEl);
          break;
        case 'question':
          await handleQuestion(postData, postEl);
          break;
        default:
          console.warn('[LEA] Unknown action:', action);
      }
    } catch (err) {
      if (err.message?.includes('Extension context invalidated')) {
        window.LEA?.showToast(
          'Extension was reloaded — please refresh this page (F5) to reconnect.',
          'error',
          8000
        );
      } else {
        console.error('[LEA] Action error:', err);
        window.LEA?.showToast('Something went wrong. Check your connection.', 'error');
      }
    } finally {
      window.LEA?.setButtonLoading(triggerBtn, false);
    }
  }

  async function handleDraftReply(postData, tone, persona, postEl) {
    const content = (postData.content || '').trim();
    if (!content) {
      window.LEA?.showToast('No post text found — try scrolling the post fully into view.', 'error', 4000);
      return;
    }

    const result = await sendMessage('DRAFT_REPLY', {
      author_name: postData.author?.name || '',
      author_role: postData.author?.headline || '',
      post_content: content.slice(0, 10_000),
      media_context: formatMediaContext(postData.media).slice(0, 2000),
      tone,
      persona,
    });

    if (!result?.success) {
      const isAuthError = result?.status === 401 || result?.status === 403;
      const isNetworkError = !result?.status && (
        !result?.error ||
        result?.error === 'extension_invalidated' ||
        /fetch|network|ECONNREFUSED|Failed to fetch/i.test(result?.error)
      );
      const msg = isAuthError
        ? 'API key not configured. Open the extension popup → ⚙ Settings to set it.'
        : isNetworkError
          ? 'Cannot reach backend. Make sure the server is running on http://localhost:8000.'
          : result?.error || 'Failed to generate reply.';
      window.LEA?.showToast(msg, 'error', 5000);
      return;
    }

    window.LEA?.showReplyPanel(postEl, result.data, (draftText) => {
      const inserted = window.LEA?.insertDraftText(draftText);
      if (!inserted) {
        window.LEA?.showToast('Click the comment box first, then insert.', 'info', 4000);
      }
    });
    _recordProductiveAction(45); // reply drafting = ~45s productive
  }

  async function handleSummarize(postData, postEl) {
    const result = await sendMessage('ANALYZE_POST', {
      content: (postData.content || '').slice(0, 10_000),
      mode: 'summarize',
    });

    if (!result?.success) {
      const msg = result?.status === 401 || result?.status === 403
        ? 'API key not configured. Open the extension popup → ⚙ Settings to set it.'
        : result?.error || 'Failed to summarize.';
      window.LEA?.showToast(msg, 'error', 5000);
      return;
    }

    window.LEA?.showReplyPanel(
      postEl,
      {
        reply: result.data?.summary || '',
        reasoning: '',
        engagement_score: null,
      },
      null
    );
  }

  async function handleContrarian(postData, postEl) {
    const result = await sendMessage('DRAFT_REPLY', {
      author_name: postData.author?.name || '',
      author_role: postData.author?.headline || '',
      post_content: (postData.content || '').slice(0, 10_000),
      media_context: formatMediaContext(postData.media).slice(0, 2000),
      tone: 'contrarian',
      persona: 'senior_engineer',
    });

    if (!result?.success) {
      const msg = result?.status === 401 || result?.status === 403
        ? 'API key not configured. Open the extension popup → ⚙ Settings to set it.'
        : result?.error || 'Failed to generate contrarian take.';
      window.LEA?.showToast(msg, 'error', 5000);
      return;
    }

    window.LEA?.showReplyPanel(postEl, result.data, (draftText) => {
      window.LEA?.insertDraftText(draftText);
    });
  }

  async function handleQuestion(postData, postEl) {
    const result = await sendMessage('DRAFT_REPLY', {
      author_name: postData.author?.name || '',
      author_role: postData.author?.headline || '',
      post_content: (postData.content || '').slice(0, 10_000),
      media_context: formatMediaContext(postData.media).slice(0, 2000),
      tone: 'thoughtful_question',
      persona: 'researcher',
    });

    if (!result?.success) {
      const msg = result?.status === 401 || result?.status === 403
        ? 'API key not configured. Open the extension popup → ⚙ Settings to set it.'
        : result?.error || 'Failed to generate question.';
      window.LEA?.showToast(msg, 'error', 5000);
      return;
    }

    window.LEA?.showReplyPanel(postEl, result.data, (draftText) => {
      window.LEA?.insertDraftText(draftText);
    });
  }

  // ---------------------------------------------------------------------------
  // Settings helper
  // ---------------------------------------------------------------------------

  async function getSettings() {
    const result = await sendMessage('GET_SETTINGS');
    return result?.data || {};
  }

  // ---------------------------------------------------------------------------
  // Messaging helper (content scripts cannot import modules)
  // ---------------------------------------------------------------------------

  /**
   * Send a message to the background service worker with retry logic.
   *
   * In MV3, the service worker is ephemeral and may be terminated when idle.
   * The first sendMessage attempt can fail with "Could not establish connection"
   * while Chrome is restarting the worker. Retrying after a short delay fixes this.
   */
  function sendMessage(type, payload, retries = 3) {
    return new Promise((resolve) => {
      function attempt(attemptsLeft) {
        // chrome.runtime may be undefined if the extension was removed
        if (!chrome.runtime?.sendMessage) {
          window.LEA?.showToast(
            'Extension was reloaded — please refresh this page (F5) to reconnect.',
            'error',
            8000
          );
          resolve({ success: false, error: 'extension_invalidated' });
          return;
        }

        try {
          chrome.runtime.sendMessage({ type, payload }, (response) => {
            if (chrome.runtime.lastError) {
              const msg = chrome.runtime.lastError.message || '';
              if (attemptsLeft > 1 && msg.includes('Could not establish connection')) {
                // Service worker is restarting — wait briefly then retry
                setTimeout(() => attempt(attemptsLeft - 1), 300);
                return;
              }
              if (msg.includes('Extension context invalidated')) {
                // Extension was reloaded while this page was open — page refresh required
                window.LEA?.showToast(
                  'Extension was reloaded — please refresh this page (F5) to reconnect.',
                  'error',
                  8000
                );
                resolve({ success: false, error: 'extension_invalidated' });
                return;
              }
              console.error('[LEA] Message error:', msg);
              resolve({ success: false, error: msg });
              return;
            }
            resolve(response);
          });
        } catch (err) {
          // Thrown synchronously when the extension context is already gone
          if (err.message?.includes('Extension context invalidated')) {
            window.LEA?.showToast(
              'Extension was reloaded — please refresh this page (F5) to reconnect.',
              'error',
              8000
            );
            resolve({ success: false, error: 'extension_invalidated' });
          } else {
            resolve({ success: false, error: err.message });
          }
        }
      }
      attempt(retries);
    });
  }

  // ---------------------------------------------------------------------------
  // Media context formatter
  // ---------------------------------------------------------------------------

  function formatMediaContext(media) {
    if (!media || !Array.isArray(media) || media.length === 0) return '';
    return media.map((m) => `[${m.type}: ${m.description}]`).join(', ');
  }

  // ---------------------------------------------------------------------------
  // MutationObserver — SPA-aware feed observation
  // ---------------------------------------------------------------------------

  const debouncedProcessPosts = debounce(processPosts, DEBOUNCE_MS);

  function startObserver() {
    const feedRoot = document.querySelector(SELECTORS.FEED_ROOT) || document.body;

    const observer = new MutationObserver((mutations) => {
      let hasNewNodes = false;
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          hasNewNodes = true;
          break;
        }
      }
      if (hasNewNodes) debouncedProcessPosts();
    });

    observer.observe(feedRoot, {
      childList: true,
      subtree: true,
    });

    console.log('[LEA] Feed observer started on', feedRoot.tagName || 'document.body');
    return observer;
  }

  // ---------------------------------------------------------------------------
  // Route change detection (LinkedIn is a SPA)
  // ---------------------------------------------------------------------------

  let currentPathname = window.location.pathname;

  function onRouteChange() {
    if (window.location.pathname !== currentPathname) {
      currentPathname = window.location.pathname;
      // Clear processed flags so buttons re-inject after navigation
      document.querySelectorAll('[data-lea-processed]').forEach((el) => {
        el.removeAttribute('data-lea-processed');
      });
      // Remove any lingering reply panels
      document.querySelectorAll('[data-lea-injected]').forEach((el) => {
        if (el.classList.contains('lea-reply-panel') || el.classList.contains('lea-toast')) {
          el.remove();
        }
      });
      debounce(processPosts, 1000)();
    }
  }

  // Intercept pushState / replaceState for SPA navigation
  const _pushState = history.pushState.bind(history);
  history.pushState = function (...args) {
    _pushState(...args);
    onRouteChange();
  };

  const _replaceState = history.replaceState.bind(history);
  history.replaceState = function (...args) {
    _replaceState(...args);
    onRouteChange();
  };

  window.addEventListener('popstate', onRouteChange);

  // ---------------------------------------------------------------------------
  // Initialise
  // ---------------------------------------------------------------------------

  function init() {
    // Wait for LinkedIn's main content to load
    const waitForFeed = setInterval(() => {
      const feed = document.querySelector(SELECTORS.FEED_ROOT);
      if (feed) {
        clearInterval(waitForFeed);
        processPosts();
        startObserver();
        console.log('[LEA] Content script initialised on', window.location.hostname);
      }
    }, 500);

    // Hard timeout — init anyway after 5s even if feed selector not found
    setTimeout(() => {
      clearInterval(waitForFeed);
      processPosts();
      startObserver();
    }, 5000);

    // Start time tracking
    startTimeTracking();

    // Detect LinkedIn analytics pages and extract data for the Analytics tab
    checkAnalyticsPage();
  }

  // ---------------------------------------------------------------------------
  // Time tracking (activity monitoring — no content, just seconds)
  // ---------------------------------------------------------------------------

  const _timeData = {
    activeSeconds: 0,
    idleSeconds: 0,
    pageViews: 1,
    actionsTaken: 0,
    productiveSeconds: 0,
    lastActivity: Date.now(),
    sessionStart: Date.now(),
  };
  const _IDLE_THRESHOLD_MS = 60_000; // 60 seconds of no activity = idle
  const _REPORT_INTERVAL_MS = 5 * 60_000; // Report every 5 minutes

  function _onActivity() {
    _timeData.lastActivity = Date.now();
  }

  function startTimeTracking() {
    // Activity listeners
    ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'].forEach((evt) => {
      document.addEventListener(evt, _onActivity, { passive: true });
    });

    // Tick every second
    setInterval(() => {
      if (document.hidden || (Date.now() - _timeData.lastActivity) > _IDLE_THRESHOLD_MS) {
        _timeData.idleSeconds++;
      } else {
        _timeData.activeSeconds++;
      }
    }, 1000);

    // Report to background every 5 minutes
    setInterval(_flushTimeSession, _REPORT_INTERVAL_MS);

    // Final report on tab close
    window.addEventListener('beforeunload', _flushTimeSession, { once: true });
  }

  function _flushTimeSession() {
    if (_timeData.activeSeconds === 0 && _timeData.idleSeconds === 0) return;

    const payload = {
      session_date: new Date().toISOString().slice(0, 10),
      active_seconds: _timeData.activeSeconds,
      idle_seconds: _timeData.idleSeconds,
      page_views: _timeData.pageViews,
      actions_taken: _timeData.actionsTaken,
      productive_seconds: _timeData.productiveSeconds,
    };

    // Reset counters
    _timeData.activeSeconds = 0;
    _timeData.idleSeconds = 0;
    _timeData.pageViews = 0;
    _timeData.actionsTaken = 0;
    _timeData.productiveSeconds = 0;

    sendMessage('LOG_TIME_SESSION', payload).catch(() => {});
  }

  /** Called by action handlers to record productive AI-assisted time. */
  function _recordProductiveAction(estimatedSeconds = 30) {
    _timeData.actionsTaken++;
    _timeData.productiveSeconds += estimatedSeconds;
  }

  // ---------------------------------------------------------------------------
  // Analytics page detection
  // ---------------------------------------------------------------------------

  function checkAnalyticsPage() {
    if (!location.href.includes('/analytics/')) return;
    if (typeof LEA?.extractAnalyticsPage !== 'function') return;

    // Wait for the analytics DOM to populate (LinkedIn SPA renders async)
    let attempts = 0;
    const poller = setInterval(() => {
      const data = LEA.extractAnalyticsPage();
      if (data || ++attempts >= 20) {
        clearInterval(poller);
        if (data) {
          chrome.runtime.sendMessage({ type: 'STORE_ANALYTICS', payload: data }, () => {
            if (chrome.runtime.lastError) {/* SW may be inactive — ignore */}
          });
        }
      }
    }, 500);
  }

  // Re-check on SPA navigation to analytics
  window.addEventListener('popstate', () => checkAnalyticsPage());

  // Remove the global guard flag after a short delay so it's not detectable
  // long-term (the WeakSet keeps the processed-post state in memory instead)
  setTimeout(() => { try { delete window.__LEA_CONTENT_LOADED__; } catch {} }, 2000);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
