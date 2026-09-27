import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ta } from './ta';
import { setActiveLanguage } from './locale';

/**
 * Bilingual support (English / தமிழ்).
 *
 * Translation is keyed by the English source string, so a component reads
 * `t('Add doctor')` and nothing has to invent or maintain key names. Any string
 * missing from the Tamil dictionary falls back to the English original, which
 * means a partially-translated screen degrades to readable English rather than
 * to blank labels or key names.
 */

export const LANGUAGES = [
  { code: 'en', label: 'English', short: 'EN', speech: 'en-IN' },
  { code: 'ta', label: 'தமிழ்', short: 'த', speech: 'ta-IN' },
];

const DICTIONARIES = { en: {}, ta };
const STORAGE_KEY = 'ehm.language';
const DEFAULT_LANGUAGE = 'en';

function readStoredLanguage() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && DICTIONARIES[stored]) return stored;
  } catch {
    /* private mode or blocked storage — fall through to the default */
  }
  return DEFAULT_LANGUAGE;
}

/** Translate outside of a React component (formatters, service messages). */
export function translate(language, text, vars) {
  if (text === null || text === undefined) return text;
  const source = String(text);
  const dictionary = DICTIONARIES[language] || {};
  let out = dictionary[source] || source;
  if (vars) {
    Object.keys(vars).forEach((name) => {
      out = out.split(`{${name}}`).join(String(vars[name]));
    });
  }
  return out;
}

const LanguageContext = createContext({
  language: DEFAULT_LANGUAGE,
  setLanguage: () => {},
  t: (text) => text,
  speechLocale: 'en-IN',
});

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    const initial = readStoredLanguage();
    setActiveLanguage(initial);
    return initial;
  });

  const setLanguage = useCallback((code) => {
    if (!DICTIONARIES[code]) return;
    setLanguageState(code);
    setActiveLanguage(code);
    try {
      window.localStorage.setItem(STORAGE_KEY, code);
    } catch {
      /* storage is a convenience here, never a requirement */
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('lang', language);
    setActiveLanguage(language);
  }, [language]);

  const value = useMemo(() => {
    const t = (text, vars) => translate(language, text, vars);
    const entry = LANGUAGES.find((item) => item.code === language) || LANGUAGES[0];
    return { language, setLanguage, t, speechLocale: entry.speech };
  }, [language, setLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}

/** The common case: `const t = useT();` then `t('Save')`. */
export function useT() {
  return useContext(LanguageContext).t;
}

export default LanguageContext;
