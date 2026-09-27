/**
 * The active language, readable outside React.
 *
 * Date and relative-time formatting happens in plain helper functions that are
 * called from dozens of render sites. Rather than thread a hook through all of
 * them, the provider publishes the current language here and the formatters
 * read it. The React context remains the source of truth; this is a mirror.
 */
let current = 'en';

export function setActiveLanguage(code) {
  current = code || 'en';
}

export function activeLanguage() {
  return current;
}

/** The BCP-47 tag `Intl` should use for the active language. */
export function activeLocale() {
  return current === 'ta' ? 'ta-IN' : undefined;
}
