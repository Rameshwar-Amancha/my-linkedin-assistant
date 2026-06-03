/**
 * sanitize.js — HTML sanitization utilities
 *
 * Prevents XSS when inserting AI-generated text into the DOM.
 * Uses an allowlist approach — only safe tags and attributes pass through.
 * eval() is NEVER used anywhere in this codebase.
 */

/** Allowed HTML tags for rich text injection */
const ALLOWED_TAGS = new Set(['b', 'i', 'em', 'strong', 'br', 'p', 'span']);

/** Allowed attributes per tag */
const ALLOWED_ATTRS = new Set(['class', 'data-lea-injected']);

/**
 * Sanitize an HTML string to prevent XSS.
 * Strips all tags not in ALLOWED_TAGS.
 * Strips all attributes not in ALLOWED_ATTRS.
 *
 * @param {string} html
 * @returns {string} sanitized HTML
 */
export function sanitizeHTML(html) {
  if (typeof html !== 'string') return '';

  // Parse in an inert document fragment to avoid script execution
  const template = document.createElement('template');
  template.innerHTML = html;
  const fragment = template.content;

  walkAndSanitize(fragment);
  const div = document.createElement('div');
  div.appendChild(fragment.cloneNode(true));
  return div.innerHTML;
}

/**
 * Sanitize plain text for safe textContent insertion.
 * Strips all HTML tags.
 *
 * @param {string} text
 * @returns {string}
 */
export function sanitizeText(text) {
  if (typeof text !== 'string') return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.textContent;
}

/**
 * Recursively walk DOM nodes and remove disallowed elements/attributes.
 * @param {Node} node
 */
function walkAndSanitize(node) {
  const children = Array.from(node.childNodes);
  for (const child of children) {
    if (child.nodeType === Node.ELEMENT_NODE) {
      const tagName = child.tagName.toLowerCase();
      if (!ALLOWED_TAGS.has(tagName)) {
        // Replace disallowed element with its text content
        const textNode = document.createTextNode(child.textContent);
        node.replaceChild(textNode, child);
        continue;
      }

      // Strip disallowed attributes
      const attrs = Array.from(child.attributes);
      for (const attr of attrs) {
        if (!ALLOWED_ATTRS.has(attr.name.toLowerCase())) {
          child.removeAttribute(attr.name);
        }
      }

      walkAndSanitize(child);
    }
  }
}

/**
 * Escape text for safe insertion into attribute values.
 * @param {string} text
 * @returns {string}
 */
export function escapeAttr(text) {
  if (typeof text !== 'string') return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
