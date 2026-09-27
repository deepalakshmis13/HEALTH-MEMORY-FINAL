import { useT } from '../../i18n/LanguageContext';

export function QuickActions({ actions = [], onPick, disabled }) {
  const t = useT();
  if (!actions.length) return null;
  return (
    <div className="quick-actions">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          className="chip"
          onClick={() => onPick(action)}
          disabled={disabled}
        >
          {t(action)}
        </button>
      ))}
    </div>
  );
}

export default QuickActions;
