import { useEffect, useState } from 'react';
import StatCard from '../common/StatCard';
import { Badge } from '../common/StatusBadge';
import { SectionCard } from '../common/PageHeader';
import LoadingState from '../common/LoadingState';
import { ErrorState } from '../common/EmptyState';
import ConfidenceIndicator from '../ingestion/ConfidenceIndicator';
import { reviewerService } from '../../services/roleServices';
import { formatDateTime } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

export function MedicationInsights() {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    reviewerService
      .insights()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState message={t('Calculating confidence…')} />;

  const maxField = Math.max(1, ...Object.values(data.tasks_by_field || {}));

  return (
    <div className="stack">
      <div className="grid grid-4">
        <StatCard
          icon="📥"
          label={t('Pending')}
          value={data.stats.pending}
          tone={data.stats.pending ? 'warn' : 'ok'}
          hint={t('{count} high priority', { count: data.stats.high_priority })}
        />
        <StatCard icon="✅" label={t('Verified')} value={data.stats.verified} tone="ok" />
        <StatCard
          icon="✏️"
          label={t('Corrected')}
          value={data.stats.corrected}
          tone="info"
          hint={
            data.correction_rate !== null
              ? t('{percent}% of all tasks', {
                  percent: Math.round(data.correction_rate * 100),
                })
              : ''
          }
        />
        <StatCard
          icon="⛔"
          label={t('Rejected')}
          value={data.stats.rejected}
          tone="danger"
        />
      </div>

      <div className="grid grid-2">
        <SectionCard
          title={t('Average OCR confidence')}
          subtitle={t('Why handwriting creates most of the verification work')}
        >
          <div className="stack">
            <ConfidenceIndicator
              value={data.average_confidence.printed_documents}
              label={t('Printed documents ({count})', {
                count: data.document_counts.printed,
              })}
            />
            <ConfidenceIndicator
              value={data.average_confidence.handwritten_documents}
              label={t('Handwritten documents ({count})', {
                count: data.document_counts.handwritten,
              })}
            />
            <ConfidenceIndicator
              value={data.average_confidence.flagged_fields}
              label={t('Fields that reached this queue')}
            />
          </div>
        </SectionCard>

        <SectionCard
          title={t('What gets flagged')}
          subtitle={t('Verification tasks by field type')}
        >
          <div className="stack">
            {Object.entries(data.tasks_by_field || {})
              .sort((a, b) => b[1] - a[1])
              .map(([field, count]) => (
                <div key={field}>
                  <div className="row between small">
                    <span>{field}</span>
                    <span className="strong">{count}</span>
                  </div>
                  <div className="confidence-track">
                    <div
                      className="confidence-fill medium"
                      style={{ width: `${(count / maxField) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            {Object.keys(data.tasks_by_field || {}).length === 0 && (
              <p className="muted">{t('No verification tasks have been created yet.')}</p>
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard title={t('Queue health')}>
        <div className="row">
          <Badge tone="outline" large>
            {t('{count} tasks in total', { count: data.stats.total })}
          </Badge>
          <Badge tone={data.stats.pending ? 'warn' : 'ok'} large>
            {t('{count} patient(s) waiting', {
              count: data.patients_with_pending.length,
            })}
          </Badge>
          {data.oldest_pending && (
            <Badge tone="outline" large>
              {t('Oldest pending since {date}', {
                date: formatDateTime(data.oldest_pending),
              })}
            </Badge>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

export default MedicationInsights;
