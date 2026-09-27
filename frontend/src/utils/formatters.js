import {
  HIGH_CONFIDENCE_THRESHOLD,
  MEDIUM_CONFIDENCE_THRESHOLD,
} from './constants';
import { activeLanguage, activeLocale } from '../i18n/locale';
import { translate } from '../i18n/LanguageContext';

/** Dates and relative times follow the language the reader chose. */
const tr = (text, vars) => translate(activeLanguage(), text, vars);

export function formatDate(value) {
  if (!value) return tr('Unknown date');
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return tr('Unknown date');
  return date.toLocaleDateString(activeLocale(), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatDateTime(value) {
  if (!value) return tr('Unknown time');
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return tr('Unknown time');
  return date.toLocaleString(activeLocale(), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function relativeTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return tr('just now');
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return tr('{n} min ago', { n: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return tr('{n} hr ago', { n: hours });
  const days = Math.floor(hours / 24);
  if (days === 1) return tr('yesterday');
  if (days < 30) return tr('{n} days ago', { n: days });
  return formatDate(value);
}

export function percent(value) {
  if (value === null || value === undefined) return '—';
  return `${Math.round(Number(value) * 100)}%`;
}

export function confidenceBand(value) {
  if (value === null || value === undefined) return 'unknown';
  if (value >= HIGH_CONFIDENCE_THRESHOLD) return 'high';
  if (value >= MEDIUM_CONFIDENCE_THRESHOLD) return 'medium';
  return 'low';
}

export function confidenceTone(value) {
  const band = confidenceBand(value);
  return band === 'high' ? 'ok' : band === 'medium' ? 'warn' : 'danger';
}

export function initials(name) {
  if (!name) return '?';
  return name
    .replace(/^Dr\.?\s*/i, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}

export function titleCase(value) {
  if (!value) return '';
  return value
    .toString()
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function truncate(text, limit = 160) {
  if (!text) return '';
  const clean = String(text).replace(/\s+/g, ' ').trim();
  return clean.length <= limit ? clean : `${clean.slice(0, limit - 1)}…`;
}

export function pluralise(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural || `${singular}s`}`;
}
