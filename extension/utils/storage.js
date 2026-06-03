/**
 * storage.js — chrome.storage.local helpers for popup/sidebar
 */

import { STORAGE_KEYS, DEFAULT_SETTINGS } from './constants.js';

export async function getSettings() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  return Object.assign({}, DEFAULT_SETTINGS, data[STORAGE_KEYS.SETTINGS] || {});
}

export async function saveSettings(updates) {
  const current = await getSettings();
  await chrome.storage.local.set({
    [STORAGE_KEYS.SETTINGS]: Object.assign({}, current, updates),
  });
}

export async function getDrafts() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.DRAFTS);
  return data[STORAGE_KEYS.DRAFTS] || [];
}

export async function getPersonas() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.PERSONAS);
  return data[STORAGE_KEYS.PERSONAS] || [];
}

export async function savePersonas(personas) {
  await chrome.storage.local.set({ [STORAGE_KEYS.PERSONAS]: personas });
}

export async function getTrendsCache() {
  const data = await chrome.storage.local.get(STORAGE_KEYS.TRENDS_CACHE);
  const cache = data[STORAGE_KEYS.TRENDS_CACHE];
  if (!cache) return null;
  // Cache valid for 30 minutes
  if (Date.now() - cache.fetchedAt > 30 * 60 * 1000) return null;
  return cache.data;
}

export async function setTrendsCache(trends) {
  await chrome.storage.local.set({
    [STORAGE_KEYS.TRENDS_CACHE]: { data: trends, fetchedAt: Date.now() },
  });
}
