/**
 * browser.js — Cross-browser WebExtension API shim
 *
 * Firefox exposes `browser.*` natively (Promise-based).
 * Chrome / Edge use `chrome.*` (also Promise-based in MV3 for most APIs).
 *
 * By preferring `browser` we get native Promises on Firefox without any
 * polyfill. On Chrome/Edge we fall back to the `chrome` global which in MV3
 * also supports Promises for most APIs (since Chrome 99, Jan 2022).
 *
 * Usage in ES-module scripts (popup, sidebar):
 *
 *   import { ext, isFirefox, hasSidePanel } from '../utils/browser.js';
 *
 *   const result = await ext.storage.local.get('lea_settings');
 *   const manifest = ext.runtime.getManifest();
 */

/**
 * Unified extension API object.
 *   Firefox → `browser`  (native, always Promise-based)
 *   Chrome / Edge → `chrome`  (MV3, Promise-based for most APIs)
 */
export const ext = (typeof globalThis.browser !== 'undefined')
  ? globalThis.browser
  : globalThis.chrome;

/**
 * True when running inside Firefox.
 * Prefer feature-detection over UA sniffing, but the presence of the
 * global `browser` object is the canonical indicator for Firefox WebExtensions.
 */
export const isFirefox = typeof globalThis.browser !== 'undefined';

/**
 * True when the Chrome Side Panel API is available (Chrome 114+ / Edge 114+).
 * Firefox uses `sidebar_action` / `browser.sidebarAction` instead.
 */
export const hasSidePanel = typeof globalThis.chrome?.sidePanel !== 'undefined';

/**
 * Open the extension sidebar / side panel in a cross-browser way.
 *
 * @param {number} [tabId] - The active tab ID (required for Chrome Side Panel).
 * @returns {Promise<void>}
 */
export async function openExtensionSidebar(tabId) {
  if (hasSidePanel) {
    // Chrome / Edge — Side Panel API
    if (tabId) {
      await globalThis.chrome.sidePanel.open({ tabId });
    } else {
      // Fallback: open on the current window without a specific tab
      await globalThis.chrome.sidePanel.open({ windowId: chrome.windows?.WINDOW_ID_CURRENT });
    }
    return;
  }

  if (isFirefox && globalThis.browser?.sidebarAction) {
    // Firefox — Sidebar Action API
    await globalThis.browser.sidebarAction.open();
    return;
  }

  // Unsupported (should not happen in a compliant browser)
  console.warn('[LEA] openExtensionSidebar: no supported sidebar API found.');
}
