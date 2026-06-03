/**
 * sidebar.js — Sidebar dashboard controller
 */

import {
  healthCheck,
  getSettings,
  saveSettings,
  getDrafts,
  deleteDraft,
  getTrends,
  generatePost,
  analyzePost,
  exportDrafts,
  getCalendar,
  createCalendarPost,
  deleteCalendarPost,
  recordABTest,
  getAnalytics,
  getUsageStats,
  resetUsageStats,
  // New features
  getOptimalTimes,
  optimizeHashtags,
  getGrowthTips,
  getAlgorithmScore,
  analyzeAuthority,
  getEngagementSuggestions,
  getLocalTimeData,
  saveTimeGoal,
} from '../utils/api.js';
import { getTrendsCache, setTrendsCache } from '../utils/storage.js';
import { ext } from '../utils/browser.js';

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  await initConnection();
  bindTabs();
  bindSettings();
  bindCompose();
  bindAnalyze();
  bindTrends();
  bindDraftsPanel();
  bindCalendar();
  bindAnalytics();
  bindGrowth();
  bindAuthority();
  // Load initial tab
  loadTrends();
});

// ---------------------------------------------------------------------------
// Connection status
// ---------------------------------------------------------------------------

async function initConnection() {
  const badge = document.getElementById('connectionBadge');
  try {
    const result = await healthCheck();
    badge.className = result?.success ? 'connection-badge connection-badge--online' : 'connection-badge connection-badge--offline';
    badge.title = result?.success ? 'Backend connected' : 'Backend offline';
  } catch {
    badge.className = 'connection-badge connection-badge--offline';
    badge.title = 'Backend offline';
  }
}

// ---------------------------------------------------------------------------
// Tab navigation
// ---------------------------------------------------------------------------

function bindTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;

      // Update tab buttons
      document.querySelectorAll('.tab-btn').forEach((b) => {
        b.classList.remove('tab-btn--active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('tab-btn--active');
      btn.setAttribute('aria-selected', 'true');

      // Update panels
      document.querySelectorAll('.tab-panel').forEach((panel) => {
        panel.hidden = true;
        panel.classList.remove('tab-panel--active');
      });

      const targetPanel = document.getElementById(`tab${capitalize(targetTab)}`);
      if (targetPanel) {
        targetPanel.hidden = false;
        targetPanel.classList.add('tab-panel--active');
      }

      // Lazy load tab content
      if (targetTab === 'trends') loadTrends();
      if (targetTab === 'drafts') loadDrafts();
      if (targetTab === 'calendar') loadCalendar();
      if (targetTab === 'analytics') loadAnalytics();
    });
  });
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ---------------------------------------------------------------------------
// Trends tab
// ---------------------------------------------------------------------------

function bindTrends() {
  document.getElementById('btnRefreshTrends').addEventListener('click', () => {
    loadTrends(true); // force refresh
  });

  document.getElementById('trendsCategory').addEventListener('change', () => {
    loadTrends(true);
  });
}

async function loadTrends(forceRefresh = false) {
  const listEl = document.getElementById('trendsList');
  const loadingEl = document.getElementById('trendsLoading');
  const category = document.getElementById('trendsCategory').value;

  // Check cache
  if (!forceRefresh) {
    const cached = await getTrendsCache();
    if (cached) {
      renderTrends(cached, listEl);
      return;
    }
  }

  loadingEl.hidden = false;
  listEl.innerHTML = '';
  listEl.appendChild(loadingEl);

  try {
    const params = category ? { category } : {};
    const result = await getTrends(params);

    if (!result?.success) {
      showError(listEl, result?.error || 'Failed to load trends.');
      return;
    }

    const trends = result.data?.trends || [];
    await setTrendsCache(trends);
    renderTrends(trends, listEl);
  } catch (err) {
    showError(listEl, 'Network error loading trends.');
  }
}

function renderTrends(trends, container) {
  container.innerHTML = '';

  if (!trends.length) {
    container.innerHTML = '<p class="empty-state">No trends available. Try refreshing.</p>';
    return;
  }

  trends.forEach((trend) => {
    const item = document.createElement('div');
    item.className = 'trend-item';

    const scoreClass = (trend.engagement_potential || 0) >= 7 ? 'high' :
                       (trend.engagement_potential || 0) >= 4 ? 'mid' : 'low';

    item.innerHTML = `
      <div class="trend-header">
        <span class="trend-topic"></span>
        <span class="trend-score trend-score--${scoreClass}">${trend.engagement_potential || '?'}</span>
      </div>
      <p class="trend-source"></p>
      <p class="trend-angle"></p>
      <button class="trend-compose-btn" type="button">✎ Compose post</button>
    `;

    // Use textContent for user-visible data to prevent XSS
    item.querySelector('.trend-topic').textContent = trend.topic || '';
    item.querySelector('.trend-source').textContent = `📍 ${trend.source || 'Unknown'}`;
    item.querySelector('.trend-angle').textContent = trend.suggested_angle || '';

    item.querySelector('.trend-compose-btn').addEventListener('click', () => {
      // Switch to compose tab and pre-fill
      switchToCompose(trend.topic);
    });

    container.appendChild(item);
  });
}

function switchToCompose(topic) {
  document.querySelector('[data-tab="compose"]').click();
  document.getElementById('composeTopic').value = topic;
  updateCharCount('composeTopic', 'composeTopicCount');
}

// ---------------------------------------------------------------------------
// Drafts tab
// ---------------------------------------------------------------------------

function bindDraftsPanel() {
  const exportBtn = document.getElementById('btnExportDrafts');
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      setLoading(exportBtn, true, '↓ Exporting...');
      try {
        const result = await exportDrafts();
        if (!result?.success) {
          showToast(result?.error || 'Export failed.', 'error');
        } else {
          // Trigger download via a temporary anchor element
          const a = document.createElement('a');
          a.href = result.data.dataUri;
          a.download = result.data.filename || 'lea_drafts.csv';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          showToast('CSV downloaded.', 'success');
        }
      } finally {
        setLoading(exportBtn, false, '↓ Export');
      }
    });
  }
}

async function loadDrafts() {
  const listEl = document.getElementById('sidebarDraftsList');
  const result = await getDrafts();
  const allDrafts = result?.data || [];

  renderDrafts(allDrafts, listEl);

  // Wire up search
  const searchInput = document.getElementById('draftsSearch');
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase();
    const filtered = allDrafts.filter(
      (d) => d.content?.toLowerCase().includes(query) || d.label?.toLowerCase().includes(query)
    );
    renderDrafts(filtered, listEl);
  });
}

function renderDrafts(drafts, container) {
  container.innerHTML = '';

  if (!drafts.length) {
    container.innerHTML = '<p class="empty-state">No saved drafts.</p>';
    return;
  }

  drafts.forEach((draft) => {
    const item = document.createElement('div');
    item.className = 'draft-card';

    const label = document.createElement('div');
    label.className = 'draft-label';
    label.textContent = draft.label || 'Untitled draft';

    const preview = document.createElement('p');
    preview.className = 'draft-preview';
    preview.textContent = draft.content?.slice(0, 140) + (draft.content?.length > 140 ? '…' : '');

    const meta = document.createElement('div');
    meta.className = 'draft-meta';
    meta.textContent = formatDate(draft.createdAt) + (draft.tone ? ` · ${draft.tone}` : '');

    const actions = document.createElement('div');
    actions.className = 'draft-card-actions';

    const copyBtn = createBtn('Copy', 'draft-action-btn', async () => {
      await navigator.clipboard.writeText(draft.content);
      showToast('Copied!', 'success');
    });

    const deleteBtn = createBtn('Delete', 'draft-action-btn draft-action-btn--danger', async () => {
      await deleteDraft(draft.id);
      item.remove();
      checkEmpty(container, '.draft-card', 'No saved drafts.');
    });

    actions.appendChild(copyBtn);
    actions.appendChild(deleteBtn);

    item.appendChild(label);
    item.appendChild(preview);
    item.appendChild(meta);
    item.appendChild(actions);
    container.appendChild(item);
  });
}

// ---------------------------------------------------------------------------
// Compose tab
// ---------------------------------------------------------------------------

function bindCompose() {
  const topicArea = document.getElementById('composeTopic');
  topicArea.addEventListener('input', () => updateCharCount('composeTopic', 'composeTopicCount'));

  document.getElementById('btnCompose').addEventListener('click', handleCompose);
  document.getElementById('btnRegenerate').addEventListener('click', handleCompose);
}

// Store last compose params for A/B tracking
let _lastComposeParams = null;

async function handleCompose() {
  const topic = document.getElementById('composeTopic').value.trim();
  if (!topic) {
    showToast('Please enter a topic.', 'error');
    return;
  }

  const btn = document.getElementById('btnCompose');
  const regenBtn = document.getElementById('btnRegenerate');
  const style = document.getElementById('composeStyle').value;
  const tone = document.getElementById('composeTone').value;
  const persona = document.getElementById('composePersona').value;
  const variations = parseInt(document.getElementById('composeVariations').value, 10);
  const includeCta = document.getElementById('composeIncludeCta').checked;
  const includeHashtags = document.getElementById('composeIncludeHashtags').checked;

  _lastComposeParams = { topic, style, tone, persona };

  setLoading(btn, true, '✦ Generating...');

  try {
    const result = await generatePost({
      topic, style, tone, persona, variations,
      include_cta: includeCta,
      include_hashtags: includeHashtags,
    });

    if (!result?.success) {
      showToast(result?.error || 'Generation failed.', 'error');
      return;
    }

    renderVariations(result.data?.variations || [], style, tone, persona);
  } finally {
    setLoading(btn, false, '✦ Generate Post');
    regenBtn.style.display = 'inline-flex';
  }
}

function renderVariations(variations, style, tone, persona) {
  const resultsEl = document.getElementById('composeResults');
  const listEl = document.getElementById('variationsList');

  listEl.innerHTML = '';

  if (!variations.length) {
    showToast('No variations returned.', 'error');
    return;
  }

  // Simple hash for topic (used for A/B tracking grouping)
  const topic = _lastComposeParams?.topic || '';
  const topicHash = simpleHash(topic);

  variations.forEach((v, idx) => {
    const card = document.createElement('div');
    card.className = 'variation-card';

    const header = document.createElement('div');
    header.className = 'variation-header';

    const num = document.createElement('span');
    num.className = 'variation-num';
    num.textContent = `Variation ${idx + 1}`;

    const score = document.createElement('span');
    score.className = 'variation-score';
    score.textContent = v.engagement_prediction ? `Score: ${v.engagement_prediction}/10` : '';

    header.appendChild(num);
    header.appendChild(score);

    const body = document.createElement('pre');
    body.className = 'variation-content';
    body.textContent = v.content || '';

    const actions = document.createElement('div');
    actions.className = 'variation-actions';

    if (v.hashtags?.length) {
      const tags = document.createElement('div');
      tags.className = 'hashtag-list';
      v.hashtags.forEach((tag) => {
        const tagEl = document.createElement('span');
        tagEl.className = 'hashtag';
        tagEl.textContent = tag;
        tags.appendChild(tagEl);
      });
      card.appendChild(tags);
    }

    const copyBtn = createBtn('Copy', 'btn-outline', async () => {
      const text = v.hashtags?.length
        ? `${v.content}\n\n${v.hashtags.join(' ')}`
        : v.content;
      await navigator.clipboard.writeText(text);
      showToast('Copied!', 'success');
    });

    // "Use This" button — records A/B selection
    const useBtn = createBtn('✓ Use This', 'btn-primary-small', async () => {
      await navigator.clipboard.writeText(
        v.hashtags?.length ? `${v.content}\n\n${v.hashtags.join(' ')}` : v.content
      );
      // Record A/B test selection
      try {
        await recordABTest({
          topic_hash: topicHash,
          style: style || _lastComposeParams?.style || 'professional',
          tone: tone || _lastComposeParams?.tone || 'professional',
          persona: persona || _lastComposeParams?.persona || 'senior_engineer',
          variation_index: idx,
          engagement_prediction: v.engagement_prediction || 5,
        });
      } catch (e) {
        // A/B tracking is non-critical — swallow errors silently
      }
      showToast('Copied & selection recorded!', 'success');
    });

    const saveBtn = createBtn('Save Draft', 'btn-outline', async () => {
      const res = await ext.runtime.sendMessage({
        type: 'SAVE_DRAFT',
        payload: { content: v.content, label: 'Generated post', tone: 'ai-generated' },
      });
      if (res?.success) showToast('Draft saved!', 'success');
    });

    actions.appendChild(useBtn);
    actions.appendChild(copyBtn);
    actions.appendChild(saveBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);
    listEl.appendChild(card);
  });

  resultsEl.hidden = false;
  resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ---------------------------------------------------------------------------
// Content Calendar tab
// ---------------------------------------------------------------------------

function bindCalendar() {
  const newPostBtn = document.getElementById('btnNewCalendarPost');
  const saveBtn = document.getElementById('btnSaveCalendarPost');
  const cancelBtn = document.getElementById('btnCancelCalendarPost');
  const statusFilter = document.getElementById('calendarStatusFilter');

  newPostBtn?.addEventListener('click', () => {
    document.getElementById('calendarForm').hidden = false;
    newPostBtn.hidden = true;
  });

  cancelBtn?.addEventListener('click', () => {
    document.getElementById('calendarForm').hidden = true;
    document.getElementById('btnNewCalendarPost').hidden = false;
    clearCalendarForm();
  });

  saveBtn?.addEventListener('click', handleCreateCalendarPost);
  statusFilter?.addEventListener('change', loadCalendar);
}

async function loadCalendar() {
  const listEl = document.getElementById('calendarList');
  const statusFilter = document.getElementById('calendarStatusFilter').value;

  listEl.innerHTML = '<p class="empty-state">Loading...</p>';

  try {
    const params = statusFilter ? { status: statusFilter } : {};
    const result = await getCalendar(params);

    if (!result?.success) {
      showError(listEl, result?.error || 'Failed to load calendar.');
      return;
    }

    renderCalendar(result.data?.posts || [], listEl);
  } catch (err) {
    showError(listEl, 'Network error loading calendar.');
  }
}

function renderCalendar(posts, container) {
  container.innerHTML = '';

  if (!posts.length) {
    container.innerHTML = '<p class="empty-state">No scheduled posts. Click "+ Schedule Post" to add one.</p>';
    return;
  }

  posts.forEach((post) => {
    const card = document.createElement('div');
    card.className = 'calendar-card';

    const statusClass = post.status === 'published' ? 'status--published' :
                        post.status === 'scheduled' ? 'status--scheduled' :
                        post.status === 'cancelled' ? 'status--cancelled' : 'status--draft';

    const dateStr = post.scheduled_for
      ? new Date(post.scheduled_for).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      : 'No date set';

    const header = document.createElement('div');
    header.className = 'calendar-card-header';
    header.innerHTML = `
      <span class="calendar-card-title"></span>
      <span class="status-badge ${statusClass}"></span>
    `;
    header.querySelector('.calendar-card-title').textContent = post.title || 'Untitled';
    header.querySelector('.status-badge').textContent = post.status;

    const date = document.createElement('div');
    date.className = 'calendar-card-date';
    date.textContent = `📅 ${dateStr}`;

    const preview = document.createElement('p');
    preview.className = 'calendar-card-preview';
    preview.textContent = post.content?.slice(0, 100) + (post.content?.length > 100 ? '…' : '');

    const actions = document.createElement('div');
    actions.className = 'calendar-card-actions';

    const copyBtn = createBtn('Copy', 'draft-action-btn', async () => {
      const text = post.hashtags?.length
        ? `${post.content}\n\n${post.hashtags.join(' ')}`
        : post.content;
      await navigator.clipboard.writeText(text);
      showToast('Copied!', 'success');
    });

    const markDoneBtn = createBtn('Mark Published', 'draft-action-btn', async () => {
      const res = await ext.runtime.sendMessage({
        type: 'UPDATE_CALENDAR_POST',
        payload: { id: post.id, updates: { status: 'published' } },
      });
      if (res?.success) {
        showToast('Marked as published.', 'success');
        loadCalendar();
      }
    });

    const deleteBtn = createBtn('Delete', 'draft-action-btn draft-action-btn--danger', async () => {
      const res = await deleteCalendarPost(post.id);
      if (res?.success) {
        card.remove();
        checkEmpty(container, '.calendar-card', 'No scheduled posts.');
        showToast('Post deleted.', 'info');
      }
    });

    actions.appendChild(copyBtn);
    if (post.status !== 'published') actions.appendChild(markDoneBtn);
    actions.appendChild(deleteBtn);

    card.appendChild(header);
    card.appendChild(date);
    card.appendChild(preview);
    card.appendChild(actions);
    container.appendChild(card);
  });
}

async function handleCreateCalendarPost() {
  const title = document.getElementById('calendarTitle').value.trim();
  const content = document.getElementById('calendarContent').value.trim();
  const scheduledFor = document.getElementById('calendarScheduledFor').value;

  if (!content) { showToast('Content is required.', 'error'); return; }
  if (!scheduledFor) { showToast('Please set a scheduled date/time.', 'error'); return; }

  const saveBtn = document.getElementById('btnSaveCalendarPost');
  setLoading(saveBtn, true, 'Saving...');

  try {
    const result = await createCalendarPost({
      title: title || 'Untitled',
      content,
      scheduled_for: new Date(scheduledFor).toISOString(),
    });

    if (!result?.success) {
      showToast(result?.error || 'Failed to save post.', 'error');
      return;
    }

    showToast('Post scheduled!', 'success');
    document.getElementById('calendarForm').hidden = true;
    document.getElementById('btnNewCalendarPost').hidden = false;
    clearCalendarForm();
    loadCalendar();
  } finally {
    setLoading(saveBtn, false, 'Save');
  }
}

function clearCalendarForm() {
  document.getElementById('calendarTitle').value = '';
  document.getElementById('calendarContent').value = '';
  document.getElementById('calendarScheduledFor').value = '';
}

// ---------------------------------------------------------------------------
// Analyze tab
// ---------------------------------------------------------------------------

function bindAnalyze() {
  document.getElementById('btnAnalyze').addEventListener('click', handleAnalyze);
}

async function handleAnalyze() {
  const content = document.getElementById('analyzeContent').value.trim();
  if (!content) {
    showToast('Please paste a post to analyze.', 'error');
    return;
  }

  const btn = document.getElementById('btnAnalyze');
  setLoading(btn, true, '◈ Analyzing...');

  try {
    const result = await analyzePost({ content });

    if (!result?.success) {
      showToast(result?.error || 'Analysis failed.', 'error');
      return;
    }

    renderAnalysis(result.data);
  } finally {
    setLoading(btn, false, '◈ Analyze Post');
  }
}

function renderAnalysis(data) {
  const resultsEl = document.getElementById('analyzeResults');
  const scoreCardEl = document.getElementById('scoreCard');
  const recsEl = document.getElementById('recommendations');

  const scores = data?.scores || {};
  scoreCardEl.innerHTML = '';

  const metrics = [
    { key: 'hook_strength', label: 'Hook Strength' },
    { key: 'readability', label: 'Readability' },
    { key: 'authority_signals', label: 'Authority Signals' },
    { key: 'emotional_triggers', label: 'Emotional Triggers' },
    { key: 'cta_effectiveness', label: 'CTA Effectiveness' },
    { key: 'overall', label: 'Overall Score' },
  ];

  metrics.forEach(({ key, label }) => {
    const val = scores[key] || 0;
    const row = document.createElement('div');
    row.className = 'score-row';
    row.innerHTML = `
      <span class="score-label"></span>
      <div class="score-bar-wrap">
        <div class="score-bar" style="width: ${val * 10}%" aria-valuenow="${val}" aria-valuemin="0" aria-valuemax="10"></div>
      </div>
      <span class="score-val">${val}/10</span>
    `;
    row.querySelector('.score-label').textContent = label;
    scoreCardEl.appendChild(row);
  });

  recsEl.innerHTML = '';
  const recs = data?.recommendations || [];
  if (recs.length) {
    const title = document.createElement('h3');
    title.className = 'recs-title';
    title.textContent = 'Recommendations';
    recsEl.appendChild(title);

    recs.forEach((rec) => {
      const item = document.createElement('div');
      item.className = 'rec-item';
      item.textContent = rec;
      recsEl.appendChild(item);
    });
  }

  resultsEl.hidden = false;
}

// ---------------------------------------------------------------------------
// Settings overlay
// ---------------------------------------------------------------------------

function bindSettings() {
  document.getElementById('btnSettings').addEventListener('click', openSettings);
  document.getElementById('btnCloseSettings').addEventListener('click', closeSettings);
  document.getElementById('btnSaveSettings').addEventListener('click', handleSaveSettings);

  // Close on overlay click
  document.getElementById('settingsOverlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeSettings();
  });
}

async function openSettings() {
  const result = await getSettings();
  const settings = result?.data || result || {};

  document.getElementById('settingsBackendUrl').value = settings.backendUrl || '';
  document.getElementById('settingsApiKey').value = settings.apiKey || '';
  document.getElementById('settingsLlmProvider').value = settings.llmProvider || 'openai';
  document.getElementById('settingsDebugMode').checked = settings.debugMode || false;

  document.getElementById('settingsOverlay').hidden = false;
}

function closeSettings() {
  document.getElementById('settingsOverlay').hidden = true;
}

async function handleSaveSettings() {
  const backendUrl = document.getElementById('settingsBackendUrl').value.trim();
  const apiKey = document.getElementById('settingsApiKey').value.trim();
  const llmProvider = document.getElementById('settingsLlmProvider').value;
  const debugMode = document.getElementById('settingsDebugMode').checked;

  const result = await saveSettings({ backendUrl, apiKey, llmProvider, debugMode });
  if (result?.success) {
    showToast('Settings saved!', 'success');
    closeSettings();
    await initConnection();
  } else {
    showToast(result?.error || 'Save failed.', 'error');
  }
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function showToast(message, type = 'info') {
  const toast = document.getElementById('sidebarToast');
  toast.textContent = message;
  toast.className = `toast toast--${type} toast--visible`;
  toast.hidden = false;
  setTimeout(() => {
    toast.classList.remove('toast--visible');
    setTimeout(() => { toast.hidden = true; }, 300);
  }, 3000);
}

function showError(container, message) {
  container.innerHTML = `<p class="error-state">${escapeText(message)}</p>`;
}

function escapeText(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function createBtn(text, className, onClick) {
  const btn = document.createElement('button');
  btn.className = className;
  btn.type = 'button';
  btn.textContent = text;
  btn.addEventListener('click', onClick);
  return btn;
}

function setLoading(btn, loading, loadingText) {
  if (loading) {
    btn.dataset.originalText = btn.textContent;
    btn.textContent = loadingText;
    btn.disabled = true;
  } else {
    btn.textContent = btn.dataset.originalText || loadingText;
    btn.disabled = false;
  }
}

function updateCharCount(textareaId, countId) {
  const area = document.getElementById(textareaId);
  const counter = document.getElementById(countId);
  if (area && counter) counter.textContent = area.value.length;
}

function formatDate(timestamp) {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function checkEmpty(container, itemSelector, message) {
  if (!container.querySelector(itemSelector)) {
    container.innerHTML = `<p class="empty-state">${message}</p>`;
  }
}

/**
 * Simple non-cryptographic hash for grouping A/B topics.
 * Not used for security — only for grouping analytics records.
 */
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}

// ---------------------------------------------------------------------------
// Analytics tab
// ---------------------------------------------------------------------------

function bindAnalytics() {
  document.getElementById('btnRefreshAnalytics').addEventListener('click', () => loadAnalytics());
  document.getElementById('btnResetUsageStats').addEventListener('click', async () => {
    await resetUsageStats();
    await loadAnalytics();
    showToast('Usage counters reset.', 'success');
  });
}

async function loadAnalytics() {
  try {
    const result = await getUsageStats();
    const s = result?.data || {};

    // Today cards
    document.getElementById('metricTodayReplies').textContent = s.todayReplies || 0;
    document.getElementById('metricTodayPosts').textContent = s.todayPosts || 0;
    document.getElementById('metricTodayTokens').textContent =
      s.todayTokens ? s.todayTokens.toLocaleString() : 0;

    // All-time list
    document.getElementById('usageStatProvider').textContent  = s.providerLabel || s.provider || '—';
    document.getElementById('usageStatReplies').textContent   = (s.totalReplies  || 0).toLocaleString();
    document.getElementById('usageStatPosts').textContent     = (s.totalPosts    || 0).toLocaleString();
    document.getElementById('usageStatAnalyses').textContent  = (s.totalAnalyses || 0).toLocaleString();
    document.getElementById('usageStatRequests').textContent  = (s.totalRequests || 0).toLocaleString();
    document.getElementById('usageStatTokens').textContent    = (s.totalTokens   || 0).toLocaleString();
    document.getElementById('usageStatLastUsed').textContent  = s.updatedAt
      ? new Date(s.updatedAt).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
      : '—';
  } catch (_err) {
    // Non-critical — silently ignore
  }
}

// Escape helpers for safe innerHTML injection
function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escAttr(str) {
  // Only allow LinkedIn HTTPS URLs to prevent javascript: URI injection
  if (!str || !str.startsWith('https://www.linkedin.com/')) return '#';
  return str.replace(/"/g, '&quot;');
}

// ===========================================================================
// GROWTH TAB
// ===========================================================================

function bindGrowth() {
  // Time tracker refresh
  document.getElementById('btnRefreshTime')?.addEventListener('click', () => loadTimeData());

  // Time goal save
  document.getElementById('btnSaveTimeGoal')?.addEventListener('click', async () => {
    const dailyMin = parseInt(document.getElementById('timeDailyGoal')?.value) || 30;
    const result = await saveTimeGoal({ dailyMinutes: dailyMin, weeklyMinutes: dailyMin * 5 });
    if (result?.success) {
      showToast('Time goal saved.', 'success');
      await loadTimeData();
    }
  });

  // Optimal times
  document.getElementById('btnLoadOptimalTimes')?.addEventListener('click', async () => {
    const btn = document.getElementById('btnLoadOptimalTimes');
    setLoading(btn, true, 'Loading...');
    try {
      const result = await getOptimalTimes();
      if (result?.success) renderOptimalTimes(result.data);
      else showToast(result?.error || 'Failed to load timing data.', 'error');
    } finally {
      setLoading(btn, false, 'Load');
    }
  });

  // Hashtag optimizer
  document.getElementById('btnOptimizeHashtags')?.addEventListener('click', async () => {
    const topic = document.getElementById('hashtagTopic')?.value?.trim();
    if (!topic) { showToast('Enter a post topic first.', 'warning'); return; }
    const btn = document.getElementById('btnOptimizeHashtags');
    setLoading(btn, true, 'Optimizing...');
    try {
      const result = await optimizeHashtags({
        topic,
        target_audience: document.getElementById('hashtagAudience')?.value?.trim() || '',
      });
      if (result?.success) renderHashtags(result.data);
      else showToast(result?.error || 'Hashtag optimization failed.', 'error');
    } finally {
      setLoading(btn, false, '# Optimize Hashtags');
    }
  });

  // Algorithm score
  document.getElementById('btnAlgorithmScore')?.addEventListener('click', async () => {
    const content = document.getElementById('algorithmContent')?.value?.trim();
    if (!content || content.length < 20) { showToast('Enter post content (at least 20 chars).', 'warning'); return; }
    const btn = document.getElementById('btnAlgorithmScore');
    setLoading(btn, true, 'Scoring...');
    try {
      const day = document.getElementById('algorithmDay')?.value || null;
      const hourRaw = document.getElementById('algorithmHour')?.value;
      const hour = hourRaw ? parseInt(hourRaw) : null;
      const hasMedia = document.getElementById('algorithmHasMedia')?.checked || false;
      const result = await getAlgorithmScore({
        content,
        has_media: hasMedia,
        scheduled_day: day || undefined,
        scheduled_hour: hour !== null ? hour : undefined,
      });
      if (result?.success) renderAlgorithmScore(result.data);
      else showToast(result?.error || 'Algorithm scoring failed.', 'error');
    } finally {
      setLoading(btn, false, '⚡ Score for Algorithm');
    }
  });

  // Growth tips
  document.getElementById('btnLoadGrowthTips')?.addEventListener('click', async () => {
    const btn = document.getElementById('btnLoadGrowthTips');
    setLoading(btn, true, 'Loading...');
    try {
      const result = await getGrowthTips();
      if (result?.success) renderGrowthTips(result.data);
      else showToast(result?.error || 'Failed to load growth tips.', 'error');
    } finally {
      setLoading(btn, false, 'Load Tips');
    }
  });

  // Auto-load time data when Growth tab is opened
  document.getElementById('tabBtnGrowth')?.addEventListener('click', () => {
    loadTimeData();
  });
}

async function loadTimeData() {
  try {
    const result = await getLocalTimeData();
    if (!result?.success) return;
    const d = result.data;

    document.getElementById('timeToday').textContent = d.today_active_minutes ?? '—';
    document.getElementById('timeTodayProductive').textContent = d.today_productive_minutes ?? '—';
    document.getElementById('timeWeek').textContent = d.week_active_minutes ?? '—';
    document.getElementById('timeFocusRatio').textContent = d.focus_ratio ? `${d.focus_ratio}%` : '—';

    // Progress bar
    const goal = d.goals?.dailyMinutes || 30;
    document.getElementById('timeDailyGoal').value = goal;
    const pct = Math.min(100, Math.round(((d.today_active_minutes || 0) / goal) * 100));
    document.getElementById('timeProgressWrap').hidden = false;
    document.getElementById('timeProgressLabel').textContent =
      `${d.today_active_minutes || 0} / ${goal} min today`;
    document.getElementById('timeProgressPct').textContent = `${pct}%`;
    document.getElementById('timeProgressFill').style.width = `${pct}%`;
    document.getElementById('timeProgressFill').className =
      `time-progress-fill${pct >= 100 ? ' time-progress-fill--over' : ''}`;

    // 7-day breakdown mini-bars
    const breakdown = d.daily_breakdown || [];
    if (breakdown.length) {
      const maxMin = Math.max(...breakdown.map((b) => b.active_minutes), 1);
      const html = `
        <div class="time-chart">
          ${breakdown.map((b) => {
            const h = Math.max(4, Math.round((b.active_minutes / maxMin) * 40));
            const ph = Math.max(2, Math.round((b.productive_minutes / maxMin) * 40));
            const day = new Date(b.date).toLocaleDateString(undefined, { weekday: 'short' });
            return `<div class="time-bar-col" title="${b.date}: ${b.active_minutes}min active, ${b.productive_minutes}min productive">
              <div class="time-bar" style="height:${h}px">
                <div class="time-bar-productive" style="height:${ph}px"></div>
              </div>
              <div class="time-bar-label">${day}</div>
            </div>`;
          }).join('')}
        </div>
        <div class="time-legend">
          <span class="time-legend-item time-legend-item--active">Active</span>
          <span class="time-legend-item time-legend-item--productive">Productive</span>
        </div>`;
      document.getElementById('timeBreakdown').innerHTML = html;
    }

    // Insights
    const insightsEl = document.getElementById('timeInsights');
    // We only have backend insights when backend is connected; show local summary otherwise
    const insights = [];
    if ((d.today_active_minutes || 0) > 60) {
      insights.push('⚠️ You\'ve been on LinkedIn over an hour today. Consider a break — quality > quantity.');
    }
    if (d.focus_ratio > 50) {
      insights.push(`✅ ${d.focus_ratio}% of your LinkedIn time is productive (AI-assisted). Great focus!`);
    } else if (d.focus_ratio > 0) {
      insights.push(`💡 Only ${d.focus_ratio}% of LinkedIn time is productive. Open a goal and use AI tools more intentionally.`);
    }
    if (insights.length) {
      insightsEl.innerHTML = insights.map((i) => `<p class="time-insight">${escHtml(i)}</p>`).join('');
      insightsEl.hidden = false;
    }
  } catch (_) {
    document.getElementById('timeBreakdown').innerHTML = '<p class="empty-state">Time data unavailable.</p>';
  }
}

function renderOptimalTimes(data) {
  const container = document.getElementById('optimalTimesContainer');
  const summary = document.getElementById('bestTimesSummary');
  const heatmap = document.getElementById('timingHeatmap');
  const note = document.getElementById('timingNote');

  summary.innerHTML = `
    <div class="best-times-pills">
      <span class="best-times-label">Best days:</span>
      ${(data.best_days || []).map((d) => `<span class="day-pill day-pill--best">${escHtml(d)}</span>`).join('')}
    </div>
    <div class="best-times-pills">
      <span class="best-times-label">Best hours:</span>
      ${(data.best_hours || []).map((h) => `<span class="day-pill">${h > 12 ? h - 12 + 'pm' : h + 'am'}</span>`).join('')}
    </div>`;

  // Render heatmap rows
  const hm = data.heatmap || {};
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  heatmap.innerHTML = `<div class="heatmap-grid">
    ${days.map((day) => {
      const hours = hm[day] || [];
      return `<div class="heatmap-row">
        <span class="heatmap-day">${day.slice(0, 3)}</span>
        ${Array.from({ length: 24 }, (_, h) => {
          const isHot = hours.includes(h);
          return `<span class="heatmap-cell${isHot ? ' heatmap-cell--hot' : ''}" title="${day} ${h}:00${isHot ? ' — Peak time' : ''}"></span>`;
        }).join('')}
      </div>`;
    }).join('')}
    <div class="heatmap-row heatmap-hours-row">
      <span class="heatmap-day"></span>
      ${[0,3,6,9,12,15,18,21].map((h) => `<span class="heatmap-hour-label" style="grid-column:span 3">${h}h</span>`).join('')}
    </div>
  </div>`;

  note.textContent = data.timezone_note || '';
  container.hidden = false;
}

function renderHashtags(data) {
  const results = document.getElementById('hashtagResults');
  const primary = document.getElementById('primaryHashtags');
  const secondary = document.getElementById('secondaryHashtags');
  const avoid = document.getElementById('avoidHashtags');

  function hashtagCard(h) {
    const reachColor = h.estimated_reach === 'broad' ? 'tag--broad' : h.estimated_reach === 'niche' ? 'tag--niche' : 'tag--medium';
    const engColor = h.engagement_level === 'high' ? 'eng--high' : h.engagement_level === 'low' ? 'eng--low' : 'eng--med';
    return `<div class="hashtag-card">
      <span class="hashtag-name">${escHtml(h.hashtag)}</span>
      <span class="hashtag-reach ${reachColor}">${escHtml(h.estimated_reach)}</span>
      <span class="hashtag-eng ${engColor}">${escHtml(h.engagement_level)} eng</span>
      <span class="hashtag-reason">${escHtml(h.reason)}</span>
      <button class="copy-btn-sm" onclick="navigator.clipboard.writeText('${h.hashtag.replace(/'/g, "\\'")}');this.textContent='✓'" title="Copy hashtag">⎘</button>
    </div>`;
  }

  primary.innerHTML = `<div class="hashtag-group-title">✦ Primary (use these)</div>${(data.primary_hashtags || []).map(hashtagCard).join('')}`;
  secondary.innerHTML = `<div class="hashtag-group-title">Secondary (optional)</div>${(data.secondary_hashtags || []).map(hashtagCard).join('')}`;

  if ((data.avoid_hashtags || []).length) {
    avoid.innerHTML = `<div class="hashtag-group-title hashtag-group-title--avoid">⚠ Avoid (oversaturated)</div>
      <div class="avoid-tags">${data.avoid_hashtags.map((h) => `<span class="avoid-tag">${escHtml(h)}</span>`).join('')}</div>`;
  } else {
    avoid.innerHTML = '';
  }

  results.hidden = false;
}

function renderAlgorithmScore(data) {
  const scoreCard = document.getElementById('algoScoreCard');
  const suggestionsEl = document.getElementById('algoSuggestions');
  const firstCommentEl = document.getElementById('algoFirstComment');

  const tierColor = data.distribution_tier === 'viral' ? '#22c55e' :
    data.distribution_tier === 'broad' ? '#f59e0b' : '#6b7280';
  const tierIcon = data.distribution_tier === 'viral' ? '🚀' : data.distribution_tier === 'broad' ? '📣' : '👥';

  scoreCard.innerHTML = `
    <div class="algo-score-header">
      <div class="algo-score-main">
        <span class="algo-score-number" style="color:${_scoreColor(data.algorithm_score)}">${data.algorithm_score}</span>
        <span class="algo-score-max">/10</span>
      </div>
      <div class="algo-tier" style="color:${tierColor}">${tierIcon} ${data.distribution_tier.toUpperCase()} REACH</div>
    </div>
    <div class="algo-sub-scores">
      ${_miniScore('Hook', data.hook_score)}
      ${_miniScore('Virality', data.virality_score)}
      ${_miniScore('Timing', data.timing_score)}
    </div>
    <div class="algo-meta">
      <span class="algo-meta-item">📝 ${data.word_count} words</span>
      <span class="algo-meta-item"># ${data.hashtag_count} hashtags</span>
    </div>`;

  if ((data.suggestions || []).length) {
    suggestionsEl.innerHTML = `<div class="algo-suggestions-title">Improvements</div>
      <ul class="algo-suggestions-list">${data.suggestions.map((s) => `<li>${escHtml(s)}</li>`).join('')}</ul>`;
  }

  if (data.first_comment_tip) {
    firstCommentEl.innerHTML = `
      <div class="first-comment-header">💬 First Comment Strategy</div>
      <p class="first-comment-text">${escHtml(data.first_comment_tip)}</p>
      <button class="btn-secondary btn-sm" onclick="navigator.clipboard.writeText(${JSON.stringify(data.first_comment_tip)});this.textContent='Copied ✓';setTimeout(()=>this.textContent='Copy Tip',2000)">Copy Tip</button>`;
    firstCommentEl.hidden = false;
  }

  document.getElementById('algorithmResults').hidden = false;
}

function _scoreColor(score) {
  if (score >= 8) return '#22c55e';
  if (score >= 5) return '#f59e0b';
  return '#ef4444';
}

function _miniScore(label, score) {
  return `<div class="mini-score">
    <div class="mini-score-label">${label}</div>
    <div class="mini-score-bar">
      <div class="mini-score-fill" style="width:${score * 10}%;background:${_scoreColor(score)}"></div>
    </div>
    <div class="mini-score-val">${score}/10</div>
  </div>`;
}

function renderGrowthTips(data) {
  const container = document.getElementById('growthTipsContainer');
  const weeklyFocus = document.getElementById('weeklyFocus');
  const tipsList = document.getElementById('growthTipsList');
  const levers = document.getElementById('growthLevers');

  if (data.weekly_focus) {
    weeklyFocus.innerHTML = `<div class="weekly-focus-card">
      <span class="weekly-focus-label">This Week's Focus</span>
      <p class="weekly-focus-text">${escHtml(data.weekly_focus)}</p>
    </div>`;
  }

  const impactIcon = { high: '🔥', medium: '⚡', low: '💡' };
  const catColor = { content: '#0A66C2', engagement: '#16a34a', profile: '#7c3aed', consistency: '#ea580c', network: '#0891b2' };

  tipsList.innerHTML = (data.tips || []).map((tip) => `
    <div class="growth-tip-card">
      <div class="growth-tip-header">
        <span class="growth-tip-impact" title="Impact: ${tip.impact}">${impactIcon[tip.impact] || '💡'}</span>
        <span class="growth-tip-category" style="background:${catColor[tip.category] || '#374151'}20;color:${catColor[tip.category] || '#374151'}">${escHtml(tip.category)}</span>
      </div>
      <p class="growth-tip-text">${escHtml(tip.tip)}</p>
      <div class="growth-tip-action">→ ${escHtml(tip.action)}</div>
    </div>`).join('');

  if ((data.follower_growth_levers || []).length) {
    levers.innerHTML = `<div class="levers-title">Growth Levers</div>
      <ul class="levers-list">${data.follower_growth_levers.map((l) => `<li>${escHtml(l)}</li>`).join('')}</ul>`;
  }

  container.hidden = false;
}

// ===========================================================================
// AUTHORITY TAB
// ===========================================================================

// Store last analyzed topics/score for engagement suggestions
let _lastAuthorityTopics = [];
let _lastAuthorityScore = 5;

function bindAuthority() {
  // Char counter
  const samplesTA = document.getElementById('authoritySamples');
  const samplesCount = document.getElementById('authoritySamplesCount');
  if (samplesTA && samplesCount) {
    samplesTA.addEventListener('input', () => {
      samplesCount.textContent = samplesTA.value.length;
    });
  }

  // Analyze authority
  document.getElementById('btnAnalyzeAuthority')?.addEventListener('click', async () => {
    const raw = document.getElementById('authoritySamples')?.value?.trim();
    if (!raw || raw.length < 50) {
      showToast('Paste at least one LinkedIn post (50+ chars) to analyze.', 'warning');
      return;
    }
    const btn = document.getElementById('btnAnalyzeAuthority');
    setLoading(btn, true, 'Analyzing...');
    try {
      const samples = raw.split(/\n\s*---\s*\n/).map((s) => s.trim()).filter((s) => s.length > 20);
      if (!samples.length) {
        showToast('No posts found. Separate multiple posts with --- on its own line.', 'warning');
        return;
      }
      const context = document.getElementById('authorityContext')?.value?.trim() || '';
      const result = await analyzeAuthority({ post_samples: samples, professional_context: context });
      if (result?.success) {
        _lastAuthorityTopics = result.data.topic_expertise || [];
        _lastAuthorityScore = result.data.authority_score || 5;
        renderAuthorityResults(result.data);
      } else {
        showToast(result?.error || 'Authority analysis failed.', 'error');
      }
    } finally {
      setLoading(btn, false, '🏆 Analyze Authority');
    }
  });

  // Engagement suggestions
  document.getElementById('btnGetEngagementStrategy')?.addEventListener('click', async () => {
    const btn = document.getElementById('btnGetEngagementStrategy');
    setLoading(btn, true, 'Loading...');
    try {
      const result = await getEngagementSuggestions({
        topics: _lastAuthorityTopics.join(','),
        authority_score: _lastAuthorityScore,
      });
      if (result?.success) renderEngagementStrategy(result.data);
      else showToast(result?.error || 'Failed to load strategy.', 'error');
    } finally {
      setLoading(btn, false, 'Get Strategy');
    }
  });
}

function renderAuthorityResults(data) {
  const scoreDisplay = document.getElementById('authorityScoreDisplay');
  const topicsEl = document.getElementById('authorityTopics');
  const credEl = document.getElementById('authorityCredibility');
  const summaryEl = document.getElementById('authoritySummaryText');
  const actionsEl = document.getElementById('authorityActionsContainer');

  const score = data.authority_score || 0;
  const scoreLabel = score >= 8 ? 'Thought Leader' : score >= 6 ? 'Rising Authority' : score >= 4 ? 'Building Credibility' : 'Early Stage';

  scoreDisplay.innerHTML = `
    <div class="authority-score-ring">
      <svg viewBox="0 0 80 80" class="authority-ring-svg">
        <circle cx="40" cy="40" r="34" fill="none" stroke="#e5e7eb" stroke-width="8"/>
        <circle cx="40" cy="40" r="34" fill="none" stroke="${_scoreColor(score)}" stroke-width="8"
          stroke-dasharray="${(score / 10) * 213.6} 213.6"
          stroke-dashoffset="53.4" stroke-linecap="round"/>
        <text x="40" y="44" text-anchor="middle" font-size="18" font-weight="bold" fill="${_scoreColor(score)}">${score}</text>
      </svg>
      <div class="authority-score-label">${scoreLabel}</div>
    </div>`;

  if ((data.topic_expertise || []).length) {
    topicsEl.innerHTML = `<div class="authority-section-title">Topic Expertise</div>
      <div class="topic-tags">${data.topic_expertise.map((t) =>
        `<span class="topic-tag">${escHtml(t)}</span>`).join('')}</div>`;
  }

  const cred = data.credibility_signals || {};
  const signals = [
    { key: 'uses_data_stats', label: 'Uses data & stats' },
    { key: 'uses_personal_stories', label: 'Personal stories' },
    { key: 'uses_specific_examples', label: 'Specific examples' },
    { key: 'uses_frameworks', label: 'Frameworks & models' },
    { key: 'has_contrarian_views', label: 'Contrarian POV' },
    { key: 'mentions_credentials', label: 'Credentials cited' },
  ];
  credEl.innerHTML = `<div class="authority-section-title">Credibility Signals</div>
    <div class="cred-signals">${signals.map((s) =>
      `<span class="cred-signal cred-signal--${cred[s.key] ? 'yes' : 'no'}">${cred[s.key] ? '✓' : '✕'} ${s.label}</span>`
    ).join('')}</div>`;

  if (data.authority_summary) {
    summaryEl.innerHTML = `<div class="authority-section-title">Summary</div>
      <p class="authority-summary-p">${escHtml(data.authority_summary)}</p>`;
  }

  if ((data.growth_actions || []).length) {
    actionsEl.innerHTML = `<div class="authority-section-title">Growth Actions</div>
      <ol class="authority-actions-list">${data.growth_actions.map((a) => `<li>${escHtml(a)}</li>`).join('')}</ol>`;
  }

  document.getElementById('authorityResults').hidden = false;
}

function renderEngagementStrategy(data) {
  const container = document.getElementById('engagementStrategyContainer');

  document.getElementById('engagementCadence').innerHTML =
    `<div class="engage-card engage-card--cadence">
      <span class="engage-card-label">📅 Posting Cadence</span>
      <span class="engage-card-value">${escHtml(data.posting_cadence || '3x per week')}</span>
    </div>`;

  document.getElementById('engagementOverview').innerHTML =
    data.engagement_strategy
      ? `<p class="engagement-overview-text">${escHtml(data.engagement_strategy)}</p>`
      : '';

  if ((data.topics_to_comment_on || []).length) {
    document.getElementById('engagementTopics').innerHTML =
      `<div class="engage-section-title">💬 Topics to Comment On</div>
       <ul class="engage-list">${data.topics_to_comment_on.map((t) => `<li>${escHtml(t)}</li>`).join('')}</ul>`;
  }

  if ((data.comment_templates || []).length) {
    document.getElementById('commentTemplates').innerHTML =
      `<div class="engage-section-title">✍ Comment Starters (copy-edit-post)</div>
       <div class="comment-template-list">${data.comment_templates.map((t) => `
        <div class="comment-template-item">
          <p class="comment-template-text">${escHtml(t)}</p>
          <button class="copy-btn-sm" onclick="navigator.clipboard.writeText(${JSON.stringify(t)});this.textContent='✓';setTimeout(()=>this.textContent='⎘',2000)">⎘</button>
        </div>`).join('')}</div>`;
  }

  if ((data.authority_building_content || []).length) {
    document.getElementById('authorityContentTypes').innerHTML =
      `<div class="engage-section-title">📌 Content That Builds Your Authority</div>
       <ul class="engage-list">${data.authority_building_content.map((c) => `<li>${escHtml(c)}</li>`).join('')}</ul>`;
  }

  container.hidden = false;
}

