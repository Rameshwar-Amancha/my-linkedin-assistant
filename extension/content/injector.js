/**
 * injector.js — LinkedIn DOM button injection and draft insertion
 *
 * Injects AI action buttons into LinkedIn post cards in a way that:
 *  - Matches LinkedIn's visual design language
 *  - Is idempotent (never double-injects)
 *  - Doesn't break LinkedIn's layout
 *  - Properly triggers React's synthetic event system for draft insertion
 *
 * All injected elements carry data-lea-injected="true" for identification.
 */

(function (LEA) {
  'use strict';

  const INJECTED_ATTR = 'data-lea-injected';
  const TOOLBAR_CLASS = 'lea-action-toolbar';

  // ---------------------------------------------------------------------------
  // Button injection
  // ---------------------------------------------------------------------------

  /**
   * Inject AI action buttons into a post element.
   * Idempotent — skips posts that already have buttons.
   *
   * @param {HTMLElement} postEl
   * @param {Function} onAction - callback(actionType, postData)
   */
  LEA.injectPostButtons = function (postEl, onAction) {
    // Idempotency check
    if (postEl.querySelector(`.${TOOLBAR_CLASS}`)) return;

    // Find the social actions bar (where Like/Comment/Repost live)
    const actionsBar =
      postEl.querySelector('.feed-shared-social-action-bar') ||
      postEl.querySelector('.social-actions-bar') ||
      postEl.querySelector('[data-test-id="social-actions-bar"]') ||
      postEl.querySelector('.update-v2-social-activity');

    if (!actionsBar) return;

    const toolbar = buildToolbar(postEl, onAction);
    actionsBar.appendChild(toolbar);
  };

  function buildToolbar(postEl, onAction) {
    const toolbar = document.createElement('div');
    toolbar.className = TOOLBAR_CLASS;
    toolbar.setAttribute(INJECTED_ATTR, 'true');
    toolbar.setAttribute('role', 'group');
    toolbar.setAttribute('aria-label', 'AI Engagement Tools');

    const buttons = [
      { action: 'draft_reply', icon: '✦', label: 'AI Reply', title: 'Generate AI-assisted reply' },
      { action: 'summarize', icon: '◈', label: 'Summarize', title: 'Summarize this post' },
      { action: 'contrarian', icon: '⟳', label: 'Contrarian', title: 'Generate contrarian take' },
      { action: 'question', icon: '?', label: 'Ask Question', title: 'Generate thoughtful question' },
    ];

    buttons.forEach(({ action, icon, label, title }) => {
      const btn = document.createElement('button');
      btn.className = 'lea-action-btn';
      btn.setAttribute(INJECTED_ATTR, 'true');
      btn.setAttribute('title', title);
      btn.setAttribute('aria-label', title);
      btn.setAttribute('type', 'button');
      btn.innerHTML = `<span class="lea-btn-icon" aria-hidden="true">${icon}</span><span class="lea-btn-label">${label}</span>`;

      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const postData = LEA.extractPostData ? LEA.extractPostData(postEl) : null;
        if (typeof onAction === 'function') {
          onAction(action, postData, btn);
        }
      });

      toolbar.appendChild(btn);
    });

    return toolbar;
  }

  // ---------------------------------------------------------------------------
  // Loading state management
  // ---------------------------------------------------------------------------

  LEA.setButtonLoading = function (btn, loading) {
    if (!btn) return;
    if (loading) {
      btn.classList.add('lea-loading');
      btn.disabled = true;
      btn.setAttribute('aria-busy', 'true');
    } else {
      btn.classList.remove('lea-loading');
      btn.disabled = false;
      btn.setAttribute('aria-busy', 'false');
    }
  };

  // ---------------------------------------------------------------------------
  // Draft insertion
  // ---------------------------------------------------------------------------

  /**
   * Insert generated text into LinkedIn's active comment box.
   * Handles both textarea and contenteditable inputs.
   *
   * NOTE: This only populates the text — it NEVER submits.
   * The user must manually send the comment.
   *
   * @param {string} text - The draft text to insert
   * @returns {boolean} Whether insertion succeeded
   */
  LEA.insertDraftText = function (text) {
    if (!text || typeof text !== 'string') return false;

    const sanitized = sanitizePlainText(text);

    // Try contenteditable (LinkedIn's primary comment editor)
    const contentEditable = findActiveCommentEditor();
    if (contentEditable) {
      insertIntoContentEditable(contentEditable, sanitized);
      return true;
    }

    // Fallback: standard textarea
    const textarea = document.querySelector('textarea:focus, textarea[placeholder*="comment"]');
    if (textarea) {
      dispatchReactInputEvent(textarea, sanitized);
      return true;
    }

    console.warn('[LEA] No active comment editor found for draft insertion.');
    return false;
  };

  function findActiveCommentEditor() {
    // LinkedIn uses a div[contenteditable] for comments
    const selectors = [
      'div.ql-editor[contenteditable="true"]',
      'div[contenteditable="true"][data-placeholder*="comment"]',
      'div[contenteditable="true"][data-placeholder*="Comment"]',
      'div[contenteditable="true"].mentions-texteditor__content-editable',
      '.comments-comment-box__form div[contenteditable="true"]',
    ];

    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el) return el;
    }

    // Last resort: find any focused contenteditable
    const focused = document.activeElement;
    if (focused?.isContentEditable) return focused;

    return null;
  }

  function insertIntoContentEditable(element, text) {
    element.focus();

    // Clear existing content
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);

    // Insert text via execCommand (most compatible with React's synthetic events)
    document.execCommand('insertText', false, text);

    // Fire additional events for React state sync
    element.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function dispatchReactInputEvent(element, value) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      'value'
    )?.set;

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(element, value);
    } else {
      element.value = value;
    }

    element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
  }

  // ---------------------------------------------------------------------------
  // Toast notification
  // ---------------------------------------------------------------------------

  LEA.showToast = function (message, type = 'info', duration = 3000) {
    const existing = document.getElementById('lea-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'lea-toast';
    toast.className = `lea-toast lea-toast--${type}`;
    toast.setAttribute(INJECTED_ATTR, 'true');
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.textContent = sanitizePlainText(message);

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => toast.classList.add('lea-toast--visible'));

    setTimeout(() => {
      toast.classList.remove('lea-toast--visible');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  };

  // ---------------------------------------------------------------------------
  // Reply panel (inline)
  // ---------------------------------------------------------------------------

  /**
   * Show a fixed-position AI reply panel anchored to the bottom-right of the
   * viewport. Using a fixed overlay means it's always visible regardless of
   * how many comments are on the post — the user never has to scroll to find it.
   *
   * @param {HTMLElement} postEl  - The originating post (used for context only)
   * @param {object}      result  - { reply, reasoning, engagement_score }
   * @param {Function}    onInsert - called when user clicks "Insert into comment"
   */
  LEA.showReplyPanel = function (postEl, result, onInsert) {
    // Remove any existing panel (one at a time)
    const existing = document.getElementById('lea-reply-panel');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'lea-reply-panel';
    panel.className = 'lea-reply-panel';
    panel.setAttribute(INJECTED_ATTR, 'true');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'AI Draft Reply');
    panel.setAttribute('aria-modal', 'false');

    const score = result.engagement_score || 0;
    const scoreClass = score >= 8 ? 'high' : score >= 5 ? 'mid' : 'low';

    panel.innerHTML = `
      <div class="lea-reply-panel__header">
        <span class="lea-reply-panel__title">AI Draft Reply</span>
        <span class="lea-score lea-score--${scoreClass}" title="Engagement score">${score}/10</span>
        <button class="lea-panel-close" aria-label="Close" type="button">✕</button>
      </div>
      <div class="lea-reply-panel__content">
        <p class="lea-reply-text"></p>
      </div>
      ${result.reasoning ? `<details class="lea-reasoning"><summary>Reasoning</summary><p></p></details>` : ''}
      <div class="lea-reply-panel__actions">
        <button class="lea-btn-insert lea-btn-primary" type="button">Insert into comment box</button>
        <button class="lea-btn-copy" type="button">Copy</button>
        <button class="lea-btn-save" type="button">Save draft</button>
      </div>
    `;

    // Set text content safely (no innerHTML for LLM output)
    panel.querySelector('.lea-reply-text').textContent = result.reply || '';
    const reasoningEl = panel.querySelector('.lea-reasoning p');
    if (reasoningEl) reasoningEl.textContent = result.reasoning || '';

    // Close
    panel.querySelector('.lea-panel-close').addEventListener('click', () => panel.remove());

    // Insert (explicit user action — never auto-submits)
    panel.querySelector('.lea-btn-insert').addEventListener('click', () => {
      if (typeof onInsert === 'function') onInsert(result.reply);
      LEA.showToast('Draft inserted — review and send manually.', 'success');
    });

    // Copy
    panel.querySelector('.lea-btn-copy').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(result.reply || '');
        LEA.showToast('Copied to clipboard!', 'success');
      } catch {
        LEA.showToast('Copy failed — please copy manually.', 'error');
      }
    });

    // Save
    panel.querySelector('.lea-btn-save').addEventListener('click', () => {
      chrome.runtime.sendMessage({
        type: 'SAVE_DRAFT',
        payload: { content: result.reply, tone: 'ai-generated' },
      });
      LEA.showToast('Draft saved!', 'success');
    });

    // Append to body so it renders fixed to the viewport
    document.body.appendChild(panel);

    // Slide in
    requestAnimationFrame(() => panel.classList.add('lea-reply-panel--visible'));
  };

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  function sanitizePlainText(text) {
    if (typeof text !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.textContent;
  }
})(window.LEA = window.LEA || {});
