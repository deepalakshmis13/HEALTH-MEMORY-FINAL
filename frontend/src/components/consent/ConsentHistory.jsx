import { Badge } from '../common/StatusBadge';
import EmptyState from '../common/EmptyState';
import { formatDateTime } from '../../utils/formatters';
import { SCOPE_LABELS } from '../../utils/permissions';
import { useT } from '../../i18n/LanguageContext';

export function ConsentHistory({ history = [] }) {
  const t = useT();
  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Consent history')}
          <span className="card-sub">
            {t('Every change to who can see this health memory is recorded')}
          </span>
        </h3>
      </div>
      <div className="card-body flush">
        {history.length === 0 ? (
          <EmptyState
            icon="🔐"
            title={t('No consent changes yet')}
            message={t(
              'Granting or revoking access creates an entry here and in the audit log.'
            )}
          />
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t('When')}</th>
                  <th>{t('Who')}</th>
                  <th>{t('What')}</th>
                  <th>{t('Action')}</th>
                  <th>{t('Changed by')}</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id}>
                    <td className="muted small nowrap">
                      {formatDateTime(item.created_at)}
                    </td>
                    <td className="strong">
                      {(item.grantee_role || '').replace(/_/g, ' ')}
                    </td>
                    <td>
                      {SCOPE_LABELS[item.scope]
                        ? t(SCOPE_LABELS[item.scope])
                        : item.scope}
                    </td>
                    <td>
                      <Badge tone={item.action === 'GRANTED' ? 'ok' : 'danger'}>
                        {item.action === 'GRANTED' ? t('Granted') : t('Revoked')}
                      </Badge>
                    </td>
                    <td className="muted small">{item.actor_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default ConsentHistory;
