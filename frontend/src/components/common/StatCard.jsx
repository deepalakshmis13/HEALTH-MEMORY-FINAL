import { useT } from '../../i18n/LanguageContext';

export function StatCard({ icon, label, value, hint, tone = '', onClick }) {
  const t = useT();
  const content = (
    <>
      <span className={`stat-icon ${tone}`} aria-hidden="true">
        {icon}
      </span>
      <div style={{ minWidth: 0 }}>
        <div className="stat-label">{t(label)}</div>
        <div className="stat-value">{value}</div>
        {hint && <div className="stat-hint">{t(hint)}</div>}
      </div>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        className="stat-card"
        onClick={onClick}
        style={{ textAlign: 'left', cursor: 'pointer', font: 'inherit' }}
      >
        {content}
      </button>
    );
  }
  return <div className="stat-card">{content}</div>;
}

export default StatCard;
