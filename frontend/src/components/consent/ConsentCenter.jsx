import { useCallback, useEffect, useState } from 'react';
import ConsentCard from './ConsentCard';
import ConsentHistory from './ConsentHistory';
import LoadingState from '../common/LoadingState';
import { ErrorState } from '../common/EmptyState';
import { PageHeader } from '../common/PageHeader';
import { useToast } from '../common/Toast';
import consentService from '../../services/consentService';
import { useT } from '../../i18n/LanguageContext';

export function ConsentCenter({ patientId, readOnly = false }) {
  const t = useT();
  const toast = useToast();
  const [data, setData] = useState(null);
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');
  const [busyKey, setBusyKey] = useState(null);

  const load = useCallback(() => {
    if (!patientId) return;
    setState('loading');
    consentService
      .get(patientId)
      .then((result) => {
        setData(result);
        setState('ready');
      })
      .catch((err) => {
        setError(err.message);
        setState('error');
      });
  }, [patientId]);

  useEffect(load, [load]);

  const toggle = async (granteeRole, scope, granted) => {
    const key = `${granteeRole}:${scope}`;
    setBusyKey(key);
    try {
      const result = await consentService.set({
        patientId,
        granteeRole,
        scope,
        granted,
      });
      toast.success(result.message, t('Consent updated'));
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusyKey(null);
    }
  };

  if (state === 'loading') return <LoadingState message={t('Checking consent…')} />;
  if (state === 'error') return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="stack">
      <PageHeader
        icon="🔐"
        title={t('Consent Control Center')}
        subtitle={t(
          'You decide who can see your health memory, and exactly which parts. Consent is checked before any information is retrieved — including by the AI assistants.'
        )}
      />

      {readOnly && (
        <div className="alert alert-neutral">
          <span className="alert-icon" aria-hidden="true">
            👁
          </span>
          <div className="alert-body">
            {t(
              "You are viewing this patient's consent settings. Only the patient or their guardian can change them."
            )}
          </div>
        </div>
      )}

      <div className="grid grid-2">
        {data.roles.map((role) => (
          <ConsentCard
            key={role.key}
            role={role}
            scopes={data.scopes}
            matrix={data.matrix[role.key]}
            onToggle={toggle}
            busyKey={busyKey}
            readOnly={readOnly}
          />
        ))}
      </div>

      <ConsentHistory history={data.history} />
    </div>
  );
}

export default ConsentCenter;
