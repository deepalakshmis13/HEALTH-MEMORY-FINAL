import { useCallback, useEffect, useState } from 'react';
import { Badge, SourceBadge } from '../common/StatusBadge';
import EmptyState, { ErrorState } from '../common/EmptyState';
import LoadingState from '../common/LoadingState';
import { caregiverService } from '../../services/roleServices';
import { EVENT_TYPE_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

export function InsightFeed({ patientId, refreshKey = 0 }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setData(null);
    setError('');
    caregiverService
      .insights(patientId)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [patientId]);

  useEffect(load, [load, refreshKey]);

  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Caregiver Insight Feed')}
          <span className="card-sub">
            {t(
              'Symptoms, observations, medication issues and recent changes — each with its source and time',
            )}
          </span>
        </h3>
      </div>
      <div className="card-body">
        {error && <ErrorState message={error} onRetry={load} />}
        {!data && !error && <LoadingState message="Finding relevant records…" />}
        {data?.insights?.length === 0 && (
          <EmptyState
            icon="📣"
            title="Nothing to flag"
            message="New observations, symptoms and medication events will appear here."
          />
        )}
        {data?.insights?.length > 0 && (
          <div className="stack">
            {data.insights.map((item) => (
              <div
                key={item.id}
                className={`memory-card${
                  item.severity !== 'normal' ? ' attention' : ''
                }`}
              >
                <div className="memory-card-head">
                  <h4>{item.title}</h4>
                  <Badge tone="outline">
                    {t(EVENT_TYPE_LABELS[item.event_type] || item.event_type)}
                  </Badge>
                </div>
                <div className="memory-card-body">{item.content}</div>
                <div className="memory-card-meta">
                  <span className="strong">{item.patient_name}</span>
                  <span>· {formatDate(item.event_date)}</span>
                  <SourceBadge
                    sourceType={item.source_type}
                    trustLevel={item.trust_level}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default InsightFeed;
