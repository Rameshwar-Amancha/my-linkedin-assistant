/**
 * events.js — Custom event utilities for cross-component communication
 *
 * Provides a lightweight event bus for sidebar/popup/content coordination
 * and React-compatible synthetic event dispatching for LinkedIn's DOM.
 */

// ---------------------------------------------------------------------------
// In-page event bus (for sidebar and popup)
// ---------------------------------------------------------------------------

const listeners = new Map();

export const EventBus = {
  on(event, callback) {
    if (!listeners.has(event)) listeners.set(event, new Set());
    listeners.get(event).add(callback);
    return () => this.off(event, callback); // returns unsubscribe fn
  },

  off(event, callback) {
    listeners.get(event)?.delete(callback);
  },

  emit(event, data) {
    listeners.get(event)?.forEach((cb) => {
      try {
        cb(data);
      } catch (err) {
        console.error(`[LEA] EventBus error on "${event}":`, err);
      }
    });
  },

  once(event, callback) {
    const wrapper = (data) => {
      callback(data);
      this.off(event, wrapper);
    };
    this.on(event, wrapper);
  },
};

// ---------------------------------------------------------------------------
// React synthetic event helpers for LinkedIn's React-based DOM
// ---------------------------------------------------------------------------

/**
 * Dispatch a native input event that React's synthetic event system recognises.
 * Required to properly trigger LinkedIn's React state updates when setting input values.
 *
 * @param {HTMLElement} element - The input/textarea/contenteditable element
 * @param {string} value - The text value to set
 */
export function dispatchReactInputEvent(element, value) {
  if (!element) return;

  // Get React's internal fiber/instance key
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    element.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype,
    'value'
  )?.set;

  if (nativeInputValueSetter) {
    nativeInputValueSetter.call(element, value);
  } else {
    element.value = value;
  }

  // Fire both input and change events for React compatibility
  element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
  element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
}

/**
 * Insert text into a contenteditable element (LinkedIn's comment box).
 * Triggers the necessary events for React to detect the change.
 *
 * @param {HTMLElement} element - contenteditable div
 * @param {string} text - Plain text to insert
 */
export function insertIntoContentEditable(element, text) {
  if (!element || !element.isContentEditable) return;

  element.focus();

  // Use execCommand for maximum compatibility with contenteditable
  // Note: execCommand is deprecated but remains the most reliable approach
  // for React-managed contenteditable elements in 2024
  document.execCommand('selectAll', false, null);
  document.execCommand('insertText', false, text);

  // Dispatch additional events to ensure React state sync
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'End' }));
}

/**
 * Debounce a function call.
 * @param {Function} fn
 * @param {number} ms
 * @returns {Function}
 */
export function debounce(fn, ms) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

/**
 * Throttle a function call.
 * @param {Function} fn
 * @param {number} ms
 * @returns {Function}
 */
export function throttle(fn, ms) {
  let lastCall = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastCall >= ms) {
      lastCall = now;
      return fn.apply(this, args);
    }
  };
}
