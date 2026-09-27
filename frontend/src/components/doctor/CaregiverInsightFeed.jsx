import { useEffect, useState } from 'react';
import { Badge } from '../common/StatusBadge';
import EmptyState, { ErrorState } from '../common/EmptyState';
import LoadingState from '../common/LoadingState';
import { doctorService } from '../../services/roleServices';
import { formatDate } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

export function CaregiverInsightFeed({ patientId }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!patientId) return;
    setData(null);
    setError('');
    doctorService
      .caregiverFeed(patientId)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [patientId]);

  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Caregiver Insight Feed')}
          <span className="card-sub">
            {t('What the people with the patient every day are seeing')}
          </span>
        </h3>
      </div>
      <div className="card-body">
        {error && <ErrorState message={error} />}
        {!data && !error && <LoadingState message={t('Loading caregiver notes…')} />}
        {data?.observations?.length === 0 && (
          <EmptyState
            icon="👁"
            title={t('No caregiver observations')}
            message={t('Observations recorded during care shifts will appear here.')}
          />
        )}
        {data?.observations?.length > 0 && (
          <div className="stack">
            {data.observations.map((observation) => (
              <div
                key={observation.id}
                className={`memory-card${
                  observation.severity !== 'normal' ? ' attention' : ''
                }`}
              >
                <div className="memory-card-head">
                  <h4>{observation.observation}</h4>
                  <Badge
                    tone={observation.severity === 'normal' ? 'outline' : 'warn'}
                  >
                    {observation.category}
                  </Badge>
                </div>
                <div className="memory-card-meta">
                  <span>{formatDate(observation.observed_at)}</span>
                  <Badge tone="primary">🤝 {observation.source}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default CaregiverInsightFeed;
