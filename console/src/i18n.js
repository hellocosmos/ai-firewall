import {useSyncExternalStore} from 'react';
import en from './locales/en.json';
import ko from './locales/ko.json';
import zh from './locales/zh-CN.json';
import ja from './locales/ja.json';
import es from './locales/es.json';
import fr from './locales/fr.json';

import languages from './locales/languages.json';
export {languages};
const dictionaries = {en, ko, 'zh-CN': zh, ja, es, fr};
const storageKey = 'trapdefense.locale';
const listeners = new Set();
let locale = 'en';
try {const saved = localStorage.getItem(storageKey); if (dictionaries[saved]) locale = saved;} catch {}
const legacyKeys = Object.fromEntries(Object.entries(ko).map(([key, value]) => [value, key]));
export const getLocale = () => locale;
export function setLocale(value) {
  if (!dictionaries[value]) return;
  locale = value;
  try {localStorage.setItem(storageKey, value);} catch {}
  document.documentElement.lang = value;
  for (const notify of listeners) notify();
}
export function useLocale() {
  return useSyncExternalStore(callback => {listeners.add(callback); return () => listeners.delete(callback);}, getLocale);
}
export function t(key, values = []) {
  const canonical = Object.hasOwn(en, key) ? key : legacyKeys[key] || key;
  const text = dictionaries[locale][canonical] ?? en[canonical] ?? key;
  return String(text ?? '').replace(/\{(\d+)\}/g, (match, index) => String(values[index] ?? match));
}
export const documentationUrl = () => `https://github.com/hellocosmos/ai-firewall/blob/main/docs/${locale}/console.md`;
document.documentElement.lang = locale;
