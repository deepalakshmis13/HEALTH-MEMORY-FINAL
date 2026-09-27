import { useT } from '../../i18n/LanguageContext';

export function EmptyState({
  icon = '🗂',
  title = 'Nothing here yet',
  message,
  action,
}) {
  const t = useT();
  return (
    <div className="empty-state">
      <span className="es-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="es-title">{t(title)}</div>
      {message && <p className="es-sub">{t(message)}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  const t = useT();
  return (
    <div className="empty-state">
      <span className="es-icon" aria-hidden="true">
        ⚠️
      </span>
      <div className="es-title">{t('Unable to load this section')}</div>
      <p className="es-sub">{t(message)}</p>
      {onRetry && (
        <button type="button" className="btn btn-outline" onClick={onRetry}>
          {t('Try again')}
        </button>
      )}
    </div>
  );
}

export default EmptyState;
