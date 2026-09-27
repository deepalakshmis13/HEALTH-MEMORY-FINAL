import { LANGUAGES, useLanguage } from './LanguageContext';

/**
 * The language switch. Two buttons, nothing else — it is deliberately small
 * enough to sit in the existing top bar and public nav without changing any
 * surrounding layout.
 */
export function LanguageToggle({ compact = false, className = '' }) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div
      className={`lang-toggle${compact ? ' compact' : ''}${className ? ` ${className}` : ''}`}
      role="group"
      aria-label={t('Language')}
    >
      {LANGUAGES.map((item) => (
        <button
          key={item.code}
          type="button"
          className={`lang-option${language === item.code ? ' active' : ''}`}
          onClick={() => setLanguage(item.code)}
          aria-pressed={language === item.code}
          lang={item.code}
          title={item.label}
        >
          {compact ? item.short : item.label}
        </button>
      ))}
    </div>
  );
}

export default LanguageToggle;
