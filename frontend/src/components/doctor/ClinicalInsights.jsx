import { useEffect, useState } from 'react';
import StatCard from '../common/StatCard';
import { Badge } from '../common/StatusBadge';
import { SectionCard } from '../common/PageHeader';
import LoadingState from '../common/LoadingState';
import { ErrorState } from '../common/EmptyState';
import { doctorService } from '../../services/roleServices';
import { EVENT_TYPE_LABELS } from '../../utils/constants';
import { percent } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

export function ClinicalInsights({ patientId }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!patientId) return;
    setData(null);
    setError('');
    doctorService
      .insights(patientId)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [patientId]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState message={t('Retrieving clinical history…')} />;

  const maxCount = Math.max(1, ...Object.values(data.activity_by_type || {}));

  return (
    <div className="stack">
      <div className="grid grid-4">
        <StatCard
          icon="💊"
          label={t('Active medications')}
          value={data.medication_count}
          tone="info"
        />
        <StatCard
          icon="🔍"
          label={t('Awaiting verification')}
          value={data.pending_verification}
          tone={data.pending_verification ? 'warn' : 'ok'}
          hint={
            data.pending_verification
              ? t('Not yet safe to treat as confirmed')
              : t('All extracted data confirmed')
          }
        />
        <StatCard
          icon="⚠️"
          label={t('Active alerts')}
          value={data.alerts.length}
          tone={data.alerts.length ? 'warn' : 'ok'}
        />
        <StatCard
          icon="📈"
          label={t('Entries (90 days)')}
          value={Object.values(data.activity_by_type || {}).reduce(
            (total, count) => total + count,
            0,
          )}
        />
      </div>

      {data.unverified_medications?.length > 0 && (
        <div className="alert alert-warn">
          <span className="alert-icon" aria-hidden="true">
            🔍
          </span>
          <div className="alert-body">
            <div className="alert-title">
              {t('Medication data pending reviewer verification')}
            </div>
            {data.unverified_medications
              .map(
                (medication) =>
                  t('{name} {dose} ({confidence} OCR confidence)', {
                    name: medication.name,
                    dose: medication.dose || '',
                    confidence: percent(medication.confidence),
                  }),
              )
              .join(' · ')}
            . {t('Treat as unconfirmed until verified.')}
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <SectionCard
          title={t('Health memory activity')}
          subtitle={t('Last 90 days, by record type')}
        >
          <div className="stack">
            {Object.entries(data.activity_by_type || {})
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => (
                <div key={type}>
                  <div className="row between small">
                    <span>{t(EVENT_TYPE_LABELS[type] || type)}</span>
                    <span className="strong">{count}</span>
                  </div>
                  <div className="confidence-track">
                    <div
                      className="confidence-fill high"
                      style={{ width: `${(count / maxCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            {Object.keys(data.activity_by_type || {}).length === 0 && (
              <p className="muted">{t('No activity in the last 90 days.')}</p>
            )}
          </div>
        </SectionCard>

        <div className="stack">
          <SectionCard
            title={t('Where the record comes from')}
            subtitle={t('Trust level distribution')}
          >
            <div className="row">
              {Object.entries(data.activity_by_trust_level || {}).map(
                ([level, count]) => (
                  <Badge key={level} tone="outline" large>
                    {level}: {count}
                  </Badge>
                ),
              )}
            </div>
          </SectionCard>

          <SectionCard
            title={t('Recurring symptoms')}
            subtitle={t('Reported by the patient or observed by caregivers')}
          >
            {data.recurring_symptoms.length === 0 ? (
              <p className="muted">{t('No repeated symptoms in this window.')}</p>
            ) : (
              <div className="stack">
                {data.recurring_symptoms.map((item) => (
                  <div className="row between" key={item.symptom}>
                    <span>{item.symptom}</span>
                    <Badge tone={item.count > 2 ? 'warn' : 'outline'}>
                      {item.count === 1
                        ? t('{n} mention', { n: item.count })
                        : t('{n} mentions', { n: item.count })}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

export default ClinicalInsights;
