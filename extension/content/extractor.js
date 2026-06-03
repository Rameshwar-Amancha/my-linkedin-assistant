/**
 * extractor.js — LinkedIn post data extraction
 *
 * Extracts structured post data from LinkedIn's DOM.
 * Handles: truncated posts, multilingual text, emoji content,
 * article previews, image alt text, and engagement counts.
 *
 * NOTE: This file uses no ES module imports — it is concatenated
 * with content.js via the content_scripts manifest array.
 * All exports are attached to the global window.LEA namespace.
 */

(function (LEA) {
  'use strict';

  /**
   * Extract all available data from a LinkedIn post element.
   *
   * @param {HTMLElement} postEl - The post container (.feed-shared-update-v2 or similar)
   * @returns {object} Structured post data
   */
  LEA.extractPostData = function (postEl) {
    if (!postEl) return null;

    try {
      return {
        author: extractAuthor(postEl),
        content: extractContent(postEl),
        media: extractMediaContext(postEl),
        engagement: extractEngagement(postEl),
        hashtags: extractHashtags(postEl),
        postUrl: extractPostUrl(postEl),
        extractedAt: Date.now(),
      };
    } catch (err) {
      console.error('[LEA] extractPostData error:', err);
      return null;
    }
  };

  // ---------------------------------------------------------------------------
  // Author extraction
  // ---------------------------------------------------------------------------

  function extractAuthor(postEl) {
    const name =
      postEl.querySelector('.update-components-actor__name .visually-hidden')?.textContent?.trim() ||
      postEl.querySelector('.update-components-actor__name')?.textContent?.trim() ||
      postEl.querySelector('[data-control-name="actor"] .actor-name')?.textContent?.trim() ||
      '';

    const headline =
      postEl.querySelector('.update-components-actor__description .visually-hidden')?.textContent?.trim() ||
      postEl.querySelector('.update-components-actor__description')?.textContent?.trim() ||
      '';

    const profileUrl =
      postEl.querySelector('.update-components-actor__meta-link')?.href ||
      postEl.querySelector('[data-control-name="actor"]')?.href ||
      '';

    return {
      name: sanitizeText(name),
      headline: sanitizeText(headline),
      profileUrl,
    };
  }

  // ---------------------------------------------------------------------------
  // Content extraction
  // ---------------------------------------------------------------------------

  function extractContent(postEl) {
    // Try to expand truncated posts first
    expandTruncatedContent(postEl);

    const contentEl =
      postEl.querySelector('.feed-shared-update-v2__description') ||
      postEl.querySelector('.update-components-text') ||
      postEl.querySelector('[data-test-id="main-feed-activity-card__commentary"]') ||
      postEl.querySelector('.feed-shared-text');

    if (!contentEl) return '';

    // Clone to avoid modifying live DOM
    const clone = contentEl.cloneNode(true);

    // Remove "see more" buttons from clone
    clone.querySelectorAll('.see-more, .feed-shared-inline-show-more-text__see-more-less-toggle').forEach(
      (el) => el.remove()
    );

    // Normalize whitespace while preserving line breaks
    const text = clone.innerText || clone.textContent || '';
    return sanitizeText(text.trim());
  }

  function expandTruncatedContent(postEl) {
    // Click "see more" to load full content
    const seeMoreBtn =
      postEl.querySelector('.see-more') ||
      postEl.querySelector('[data-tracking-control-name="feed-more-text"]') ||
      postEl.querySelector('.feed-shared-inline-show-more-text__see-more-less-toggle');

    if (seeMoreBtn && seeMoreBtn.textContent?.toLowerCase().includes('more')) {
      try {
        seeMoreBtn.click();
      } catch {
        // Non-critical — proceed with truncated content
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Media context extraction
  // ---------------------------------------------------------------------------

  function extractMediaContext(postEl) {
    const contexts = [];

    // Images
    postEl.querySelectorAll('img[alt]').forEach((img) => {
      const alt = img.alt?.trim();
      if (alt && alt.length > 3 && !alt.includes('profile') && !alt.includes('logo')) {
        contexts.push({ type: 'image', description: sanitizeText(alt) });
      }
    });

    // Article previews
    const articleTitle =
      postEl.querySelector('.update-components-article__title')?.textContent?.trim() ||
      postEl.querySelector('.feed-shared-article__title')?.textContent?.trim();

    if (articleTitle) {
      contexts.push({ type: 'article', description: sanitizeText(articleTitle) });
    }

    // Video
    const videoEl = postEl.querySelector('video, [data-embeds-provider]');
    if (videoEl) {
      const videoTitle = videoEl.getAttribute('aria-label') || videoEl.title || '';
      contexts.push({ type: 'video', description: sanitizeText(videoTitle) });
    }

    // Document/carousel
    const documentTitle = postEl.querySelector('.update-components-document__title')?.textContent?.trim();
    if (documentTitle) {
      contexts.push({ type: 'document', description: sanitizeText(documentTitle) });
    }

    return contexts;
  }

  // ---------------------------------------------------------------------------
  // Engagement counts
  // ---------------------------------------------------------------------------

  function extractEngagement(postEl) {
    const reactions =
      postEl.querySelector('.social-details-social-counts__reactions-count')?.textContent?.trim() ||
      postEl.querySelector('[data-test-id="social-actions__reaction-count"]')?.textContent?.trim() ||
      '0';

    const comments =
      postEl.querySelector('.social-details-social-counts__comments')?.textContent?.trim() ||
      postEl.querySelector('[data-test-id="social-actions__comments-count"]')?.textContent?.trim() ||
      '0';

    const reposts =
      postEl.querySelector('.social-details-social-counts__reposts')?.textContent?.trim() ||
      '0';

    return {
      reactions: parseEngagementNumber(reactions),
      comments: parseEngagementNumber(comments),
      reposts: parseEngagementNumber(reposts),
    };
  }

  function parseEngagementNumber(str) {
    if (!str) return 0;
    const clean = str.replace(/[^0-9KkMm.]/g, '');
    if (clean.toLowerCase().includes('k')) return Math.round(parseFloat(clean) * 1000);
    if (clean.toLowerCase().includes('m')) return Math.round(parseFloat(clean) * 1_000_000);
    return parseInt(clean, 10) || 0;
  }

  // ---------------------------------------------------------------------------
  // Hashtag extraction
  // ---------------------------------------------------------------------------

  function extractHashtags(postEl) {
    const hashtagEls = postEl.querySelectorAll(
      '.feed-shared-text a[href*="/feed/hashtag/"], a[data-tracking-control-name="hashtag"]'
    );
    const tags = [];
    hashtagEls.forEach((el) => {
      const tag = el.textContent?.trim();
      if (tag && tag.startsWith('#')) tags.push(tag);
    });
    return [...new Set(tags)]; // deduplicate
  }

  // ---------------------------------------------------------------------------
  // Post URL
  // ---------------------------------------------------------------------------

  function extractPostUrl(postEl) {
    const link =
      postEl.querySelector('a[href*="/feed/update/"]') ||
      postEl.querySelector('[data-test-id="update-components__social-activity"]');
    return link?.href || window.location.href;
  }

  // ---------------------------------------------------------------------------
  // Text sanitizer (no module import — inline implementation)
  // ---------------------------------------------------------------------------

  function sanitizeText(text) {
    if (typeof text !== 'string') return '';
    // Strip HTML tags and normalize whitespace
    const div = document.createElement('div');
    div.textContent = text;
    return div.textContent.replace(/\s+/g, ' ').trim();
  }

  // ---------------------------------------------------------------------------
  // LinkedIn Analytics page extractor
  // Targets: https://www.linkedin.com/analytics/creator/content/
  // ---------------------------------------------------------------------------

  /**
   * Extract summary metrics from LinkedIn's creator analytics dashboard.
   * Returns null when the page has not finished rendering or is not an
   * analytics page (so the caller can retry).
   *
   * @returns {object|null}
   */
  LEA.extractAnalyticsPage = function () {
    // Only run on analytics pages
    if (!location.href.includes('/analytics/')) return null;

    // Confirm at least one metrics block is present
    const metricsRoot =
      document.querySelector('.analytics-dashboard-module') ||
      document.querySelector('[data-test-id="analytics-dashboard"]') ||
      document.querySelector('.content-analytics-module') ||
      document.querySelector('section[aria-label*="nalytic"]');

    if (!metricsRoot) return null; // Not rendered yet

    const result = {
      capturedUrl: location.href,
      capturedAt: Date.now(),
      summary: extractAnalyticsSummary(),
      topPosts: extractTopPosts(),
    };

    return result;
  };

  function extractAnalyticsSummary() {
    const summary = {};

    // Impressions / Reach headline stat
    const headlineCards = document.querySelectorAll(
      '.analytics-dashboard-summary-card, [data-test-id*="summary-card"], .artdeco-stat-card'
    );

    headlineCards.forEach((card) => {
      const label = sanitizeText(
        card.querySelector('h3, .stat-title, [data-test-id*="title"]')?.textContent || ''
      ).toLowerCase();
      const value = sanitizeText(
        card.querySelector('.stat-value, .analytics-big-stat, [data-test-id*="value"], h2')?.textContent || ''
      );
      if (label && value) summary[label] = value;
    });

    // Fallback: scrape any visible large-number elements near "impressions"
    if (Object.keys(summary).length === 0) {
      document.querySelectorAll('[aria-label*="mpressions"], [aria-label*="each"]').forEach((el) => {
        const label = (el.getAttribute('aria-label') || '').toLowerCase();
        const value = sanitizeText(el.textContent);
        if (label && value) summary[label] = value;
      });
    }

    return summary;
  }

  function extractTopPosts() {
    const posts = [];

    // Try the content performance table rows
    const rows = document.querySelectorAll(
      '[data-test-id*="post-stats-row"], .analytics-post-row, .content-analytics-post-item'
    );

    rows.forEach((row, idx) => {
      if (idx >= 20) return; // Cap at 20 posts

      const titleEl = row.querySelector(
        '.post-title, [data-test-id*="post-title"], a[href*="/feed/update/"], a[href*="/posts/"]'
      );
      const impressionsEl = row.querySelector(
        '[data-test-id*="impressions"], .impressions-count, td:nth-child(2)'
      );
      const reactionsEl = row.querySelector(
        '[data-test-id*="reactions"], .reactions-count, td:nth-child(3)'
      );

      if (!titleEl) return;

      posts.push({
        title: sanitizeText(titleEl.textContent).slice(0, 200),
        postUrl: titleEl.href || null,
        impressions: sanitizeText(impressionsEl?.textContent || ''),
        reactions: sanitizeText(reactionsEl?.textContent || ''),
      });
    });

    return posts;
  }
})(window.LEA = window.LEA || {});
