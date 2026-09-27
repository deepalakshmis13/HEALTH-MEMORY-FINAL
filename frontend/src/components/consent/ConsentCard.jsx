import { SCOPE_DESCRIPTIONS, SCOPE_LABELS } from '../../utils/permissions';
import { useT } from '../../i18n/LanguageContext';

export function ConsentCard({ role, scopes, matrix, onToggle, busyKey, readOnly }) {
  const t = useT();
  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t(role.label)}
          <span className="card-sub">
            {t('What people in this role can see in this health memory')}
          </span>
        </h3>
      </div>
      <div className="card-body stack">
        {scopes.map((scope) => {
          const entry = matrix?.[scope.key];
          const granted = Boolean(entry?.granted);
          const key = `${role.key}:${scope.key}`;
          return (
            <div className="row between" key={scope.key}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="strong">
                  {t(SCOPE_LABELS[scope.key] || scope.label)}
                </div>
                <div className="small muted">
                  {t(SCOPE_DESCRIPTIONS[scope.key] || '')}
                </div>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={granted}
                  disabled={readOnly || busyKey === key}
                  onChange={(event) =>
                    onToggle(role.key, scope.key, event.target.checked)
                  }
                  aria-label={t(
                    granted ? 'Revoke {scope} for {role}' : 'Grant {scope} for {role}',
                    {
                      scope: t(SCOPE_LABELS[scope.key] || scope.label),
                      role: t(role.label),
                    }
                  )}
                />
                <span className="slider" />
              </label>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default ConsentCard;
