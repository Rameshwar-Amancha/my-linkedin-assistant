/**
 * popup.js — Popup UI controller
 */

import {
  healthCheck,
  getSettings,
  saveSettings,
  getDrafts,
  deleteDraft,
  openSidebar,
  generatePost,
  getTrends,
  getUsageStats,
  resetUsageStats,
} from '../utils/api.js';
import { ext } from '../utils/browser.js';

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  setVersion();
  await checkHealth();
  await loadSettings();
  await loadUsageStats();
  await bindEvents();
});

function setVersion() {
  const manifest = ext.runtime.getManifest();
  document.getElementById('versionLabel').textContent = `v${manifest.version}`;
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

async function checkHealth() {
  const dot = document.getElementById('statusDot');
  const label = document.getElementById('statusLabel');

  try {
    const result = await healthCheck();
    if (result?.success) {
      dot.className = 'status-dot status-dot--online';
      label.textContent = 'Connected';
    } else {
      dot.className = 'status-dot status-dot--offline';
      label.textContent = 'Offline';
    }
  } catch {
    dot.className = 'status-dot status-dot--offline';
    label.textContent = 'Offline';
  }
}

// ---------------------------------------------------------------------------
// LLM Usage stats
// ---------------------------------------------------------------------------

async function loadUsageStats() {
  try {
    const result = await getUsageStats();
    const stats = result?.data || {};

    const providerLabels = { openai: 'OpenAI gpt-4o', gemini: 'Gemini 1.5 Pro', anthropic: 'Claude 3.5' };
    const provider = stats.provider || 'openai';

    document.getElementById('usageProvider').textContent = providerLabels[provider] || provider;
    document.getElementById('usageToday').textContent =
      stats.todayTokens
        ? `${stats.todayTokens.toLocaleString()} tokens (${stats.todayRequests || 0} requests)`
        : 'No requests yet today';
    document.getElementById('usageTotal').textContent =
      stats.totalTokens
        ? `${stats.totalTokens.toLocaleString()} tokens (${stats.totalRequests || 0} total)`
        : 'None recorded';
  } catch {
    // Non-critical — silently skip
  }
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

async function loadSettings() {
  const result = await getSettings();
  const settings = result?.data || result || {};

  const toneSelect = document.getElementById('toneSelect');
  const personaSelect = document.getElementById('personaSelect');

  if (settings.defaultTone) toneSelect.value = settings.defaultTone;
  if (settings.defaultPersona) personaSelect.value = settings.defaultPersona;

  // Populate connection fields
  document.getElementById('inputBackendUrl').value = settings.backendUrl || '';
  document.getElementById('inputApiKey').value = settings.apiKey || '';
  document.getElementById('privacyMode').checked = !!settings.privacyMode;

  // Show warning banner if API key is not configured
  const warning = document.getElementById('setupWarning');
  if (!settings.apiKey) {
    warning.hidden = false;
    // Auto-expand the settings panel so user sees it immediately
    document.getElementById('connectionPanel').hidden = false;
  } else {
    warning.hidden = true;
  }
}

// ---------------------------------------------------------------------------
// Event bindings
// ---------------------------------------------------------------------------

async function bindEvents() {
  // Open sidebar
  document.getElementById('btnOpenSidebar').addEventListener('click', async () => {
    await openSidebar();
    window.close();
  });

  // Trends
  document.getElementById('btnGetTrends').addEventListener('click', async () => {
    await openSidebar();
    window.close();
  });

  // New post toggle
  document.getElementById('btnNewPost').addEventListener('click', () => {
    togglePanel('generatePostPanel');
  });

  // Drafts toggle
  document.getElementById('btnDrafts').addEventListener('click', async () => {
    togglePanel('draftsPanel');
    await loadDrafts();
  });

  // Save session settings
  document.getElementById('btnSaveSession').addEventListener('click', async () => {
    const tone = document.getElementById('toneSelect').value;
    const persona = document.getElementById('personaSelect').value;
    await saveSettings({ defaultTone: tone, defaultPersona: persona });
    showFeedback('btnSaveSession', 'Saved!');
  });

  // Generate post
  document.getElementById('btnGeneratePost').addEventListener('click', async () => {
    await handleGeneratePost();
  });

  // Open/close connection settings panel
  document.getElementById('btnSettings').addEventListener('click', () => {
    const panel = document.getElementById('connectionPanel');
    panel.hidden = !panel.hidden;
  });

  // Save connection settings
  document.getElementById('btnSaveConnection').addEventListener('click', async () => {
    const backendUrl = document.getElementById('inputBackendUrl').value.trim();
    const apiKey = document.getElementById('inputApiKey').value.trim();
    const privacyMode = document.getElementById('privacyMode').checked;
    const result = await saveSettings({ backendUrl, apiKey, privacyMode });
    if (result?.success !== false) {
      document.getElementById('setupWarning').hidden = !!apiKey;
      showFeedback('btnSaveConnection', 'Saved!', document.getElementById('btnSaveConnection'));
      // Re-check backend health with the new key
      await checkHealth();
    }
  });

  // Reset usage stats
  document.getElementById('btnResetUsage').addEventListener('click', async () => {
    await resetUsageStats();
    await loadUsageStats();
    showFeedback('btnResetUsage', 'Reset!', document.getElementById('btnResetUsage'));
  });
}

// ---------------------------------------------------------------------------
// Generate post handler
// ---------------------------------------------------------------------------

async function handleGeneratePost() {
  const topic = document.getElementById('postTopic').value.trim();
  if (!topic) {
    showError('Please enter a topic.');
    return;
  }

  const style = document.getElementById('postStyle').value;
  const includeCta = document.getElementById('includeCta').checked;
  const resultEl = document.getElementById('postResult');
  const btn = document.getElementById('btnGeneratePost');

  btn.disabled = true;
  btn.textContent = 'Generating...';
  resultEl.hidden = true;

  try {
    const result = await generatePost({ topic, style, include_cta: includeCta, variations: 1 });

    if (!result?.success) {
      showError(result?.error || 'Generation failed.');
      return;
    }

    const variation = result.data?.variations?.[0] || {};
    resultEl.hidden = false;
    resultEl.innerHTML = '';

    const pre = document.createElement('pre');
    pre.className = 'post-result-text';
    pre.textContent = variation.content || 'No content generated.';
    resultEl.appendChild(pre);

    const actions = document.createElement('div');
    actions.className = 'result-actions';
    actions.innerHTML = `
      <button class="btn-copy" type="button">Copy</button>
    `;
    resultEl.appendChild(actions);

    actions.querySelector('.btn-copy').addEventListener('click', async () => {
      await navigator.clipboard.writeText(variation.content || '');
      showFeedback('.btn-copy', 'Copied!', actions.querySelector('.btn-copy'));
    });
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate';
  }
}

// ---------------------------------------------------------------------------
// Drafts
// ---------------------------------------------------------------------------

async function loadDrafts() {
  const listEl = document.getElementById('draftsList');
  const result = await getDrafts();
  const drafts = result?.data || [];

  listEl.innerHTML = '';

  if (drafts.length === 0) {
    listEl.innerHTML = '<p class="empty-state">No saved drafts yet.</p>';
    return;
  }

  drafts.forEach((draft) => {
    const item = document.createElement('div');
    item.className = 'draft-item';

    const preview = document.createElement('p');
    preview.className = 'draft-preview';
    preview.textContent = draft.content?.slice(0, 100) + (draft.content?.length > 100 ? '...' : '');

    const actions = document.createElement('div');
    actions.className = 'draft-actions';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'draft-btn';
    copyBtn.textContent = 'Copy';
    copyBtn.type = 'button';
    copyBtn.addEventListener('click', async () => {
      await navigator.clipboard.writeText(draft.content);
      copyBtn.textContent = 'Copied!';
      setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
    });

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'draft-btn draft-btn--danger';
    deleteBtn.textContent = 'Delete';
    deleteBtn.type = 'button';
    deleteBtn.addEventListener('click', async () => {
      await deleteDraft(draft.id);
      item.remove();
      const remaining = listEl.querySelectorAll('.draft-item');
      if (remaining.length === 0) {
        listEl.innerHTML = '<p class="empty-state">No saved drafts yet.</p>';
      }
    });

    actions.appendChild(copyBtn);
    actions.appendChild(deleteBtn);
    item.appendChild(preview);
    item.appendChild(actions);
    listEl.appendChild(item);
  });
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function togglePanel(panelId) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  panel.hidden = !panel.hidden;
}

function showFeedback(selector, text, el = null) {
  const target = el || document.getElementById(selector) || document.querySelector(selector);
  if (!target) return;
  const original = target.textContent;
  target.textContent = text;
  setTimeout(() => { target.textContent = original; }, 2000);
}

function showError(msg) {
  // Simple inline error — no DOM injection risk
  const existing = document.querySelector('.popup-error');
  if (existing) existing.remove();
  const err = document.createElement('p');
  err.className = 'popup-error';
  err.textContent = msg; // textContent, not innerHTML
  document.getElementById('app').insertBefore(err, document.querySelector('.popup__section'));
  setTimeout(() => err.remove(), 4000);
}
