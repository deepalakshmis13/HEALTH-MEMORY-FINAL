import StatCard from '../common/StatCard';
import { Badge, VerificationBadge } from '../common/StatusBadge';
import EmptyState from '../common/EmptyState';
import { SectionCard } from '../common/PageHeader';
import { formatDate, percent } from '../../utils/formatters';
import { SOURCE_LABELS } from '../../utils/constants';
import { useT } from '../../i18n/LanguageContext';

export function HealthOverview({ data, plain = false, onAddData }) {
  const t = useT();
  if (!data || !data.patient) {
    return (
      <EmptyState
        icon="🩺"
        title={t('No health overview yet')}
        message={t('Once health information is added it will be summarised here.')}
        action={
          onAddData && (
            <button type="button" className="btn btn-primary" onClick={onAddData}>
              {t('Add health data')}
            </button>
          )
        }
      />
    );
  }

  const { counts = {}, alerts = [] } = data;

  return (
    <div className="stack">
      {alerts.length > 0 && (
        <div className="stack">
          {alerts.map((alert, index) => (
            <div
              key={index}
              className={`alert alert-${alert.level === 'critical' ? 'danger' : 'warn'}`}
            >
              <span className="alert-icon" aria-hidden="true">
                {alert.level === 'critical' ? '🚨' : '⚠️'}
              </span>
              <div className="alert-body">
                <div className="alert-title">{alert.title}</div>
                {alert.detail}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-4">
        <StatCard
          icon="💊"
          label={plain ? t('My medicines') : t('Active medications')}
          value={counts.active_medications ?? 0}
          hint={
            counts.recent_medication_changes
              ? t('{count} change(s) in 30 days', {
                  count: counts.recent_medication_changes,
                })
              : t('No recent changes')
          }
        />
        <StatCard
          icon="🧠"
          label={t('Health memory entries')}
          value={counts.memory_events ?? 0}
          hint={
            data.last_updated
              ? t('Last updated {date}', { date: formatDate(data.last_updated) })
              : ''
          }
          tone="info"
        />
        <StatCard
          icon="📄"
          label={t('Documents')}
          value={counts.documents ?? 0}
          hint={t('Scanned, uploaded and handwritten')}
        />
        <StatCard
          icon="🔍"
          label={t('Awaiting verification')}
          value={counts.pending_verification ?? 0}
          hint={
            counts.pending_verification
              ? t('A reviewer is confirming these')
              : t('Everything is confirmed')
          }
          tone={counts.pending_verification ? 'warn' : 'ok'}
        />
      </div>

      <div className="grid grid-2">
        <SectionCard
          title={plain ? t('My medicines') : t('Current medications')}
          subtitle={t('Every entry keeps the source it came from')}
          flush
        >
          {(data.medications || []).length === 0 ? (
            <div className="card-body">
              <p className="muted">{t('No medications recorded.')}</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{t('Medicine')}</th>
                    <th>{t('Dose')}</th>
                    <th>{t('When')}</th>
                    <th>{t('Status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.medications.map((medication) => (
                    <tr key={medication.id}>
                      <td>
                        <div className="strong">{medication.name}</div>
                        <div className="tiny faint">
                          {t(
                            SOURCE_LABELS[medication.source_type] ||
                              medication.source_type,
                          )}
                          {medication.prescriber ? ` · ${medication.prescriber}` : ''}
                        </div>
                      </td>
                      <td>{medication.dose || '—'}</td>
                      <td>{medication.frequency || '—'}</td>
                      <td>
                        <VerificationBadge
                          status={medication.verification_status}
                          confidence={medication.confidence}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <div className="stack">
          <SectionCard
            title={t('Allergies')}
            subtitle={t('Always check before prescribing')}
          >
            {(data.allergies || []).length === 0 ? (
              <p className="muted">{t('No allergies recorded.')}</p>
            ) : (
              <div className="stack">
                {data.allergies.map((allergy) => (
                  <div key={allergy.id} className="row between">
                    <div>
                      <div className="strong">{allergy.substance}</div>
                      {allergy.reaction && (
                        <div className="small muted">{allergy.reaction}</div>
                      )}
                    </div>
                    <Badge
                      tone={allergy.severity === 'severe' ? 'danger' : 'warn'}
                    >
                      {allergy.severity}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title={plain ? t('My conditions') : t('Active conditions')}>
            {(data.conditions || []).length === 0 ? (
              <p className="muted">{t('No conditions recorded.')}</p>
            ) : (
              <div className="row">
                {data.conditions.map((condition) => (
                  <Badge
                    key={condition.id}
                    tone={condition.is_critical ? 'danger' : 'outline'}
                    large
                  >
                    {condition.name}
                  </Badge>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </div>

      <div className="grid grid-2">
        <SectionCard title={t('Recent test results')} flush>
          {(data.lab_results || []).length === 0 ? (
            <div className="card-body">
              <p className="muted">{t('No laboratory results recorded.')}</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{t('Test')}</th>
                    <th>{t('Result')}</th>
                    <th>{t('Reference')}</th>
                    <th>{t('Date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lab_results.map((lab) => (
                    <tr key={lab.id}>
                      <td className="strong">{lab.test_name}</td>
                      <td>
                        {lab.value} {lab.unit}
                        {lab.flag !== 'normal' && (
                          <Badge
                            tone={lab.flag === 'critical' ? 'danger' : 'warn'}
                          >
                            {lab.flag}
                          </Badge>
                        )}
                      </td>
                      <td className="muted small">{lab.reference_range || '—'}</td>
                      <td className="muted small nowrap">
                        {formatDate(lab.tested_on)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard title={t('Hospital visits')}>
          {(data.hospital_visits || []).length === 0 ? (
            <p className="muted">{t('No hospital visits recorded.')}</p>
          ) : (
            <div className="stack">
              {data.hospital_visits.map((visit) => (
                <div key={visit.id}>
                  <div className="strong">{visit.hospital}</div>
                  <div className="small muted">
                    {formatDate(visit.admitted_on)} — {visit.reason}
                  </div>
                  {visit.summary && <div className="small">{visit.summary}</div>}
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}

export default HealthOverview;
