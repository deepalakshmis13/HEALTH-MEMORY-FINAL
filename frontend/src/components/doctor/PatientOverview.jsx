import { Badge } from '../common/StatusBadge';
import HealthOverview from '../health-memory/HealthOverview';
import { SectionCard } from '../common/PageHeader';
import { useT } from '../../i18n/LanguageContext';

export function PatientOverview({ overview, access, routing }) {
  const t = useT();
  if (!overview?.patient) return null;
  const patient = overview.patient;

  return (
    <div className="stack">
      <section className="card">
        <div className="card-header">
          <h3>
            {patient.full_name}
            <span className="card-sub">
              {[
                patient.age ? t('{age} years', { age: patient.age }) : null,
                patient.gender,
                patient.blood_group
                  ? t('Blood group {group}', { group: patient.blood_group })
                  : null,
                patient.old_age_home,
                patient.room_number
                  ? t('Room {number}', { number: patient.room_number })
                  : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            </span>
          </h3>
          {access && (
            <div className="row tight">
              <Badge tone="primary">{access.relationship}</Badge>
              <Badge tone="outline">
                {t('{n} consent scope(s)', { n: access.granted_scopes.length })}
              </Badge>
            </div>
          )}
        </div>
        {access && (
          <div className="card-body">
            <div className="row tight">
              {access.granted_scopes.map((scope) => (
                <Badge key={scope} tone="outline">
                  {scope.replace(/_/g, ' ').toLowerCase()}
                </Badge>
              ))}
            </div>
            <p className="tiny faint mt-1">
              {t(
                'Retrieval is limited to these scopes. Anything the patient has not shared is removed before the record is read — not filtered out afterwards.',
              )}
            </p>
          </div>
        )}
      </section>

      {routing && (
        <SectionCard
          title={t('Routed from a medical record')}
          subtitle={t(
            "This patient's record reached you through a document that named you",
          )}
        >
          <div className="stack">
            {routing.updates.map((update) => (
              <div className="row between" key={update.id}>
                <div>
                  <div className="strong">{update.title}</div>
                  <div className="small muted">
                    {update.date} · {update.trust_level}
                  </div>
                </div>
                <Badge
                  tone={
                    update.verification_status === 'PENDING_VERIFICATION'
                      ? 'warn'
                      : 'ok'
                  }
                >
                  {update.verification_status === 'PENDING_VERIFICATION'
                    ? t('Awaiting verification')
                    : t('Verified source')}
                </Badge>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      <HealthOverview data={overview} />
    </div>
  );
}

export default PatientOverview;
