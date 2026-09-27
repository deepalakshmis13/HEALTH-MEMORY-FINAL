import { Badge } from '../common/StatusBadge';
import EmptyState from '../common/EmptyState';
import { useT } from '../../i18n/LanguageContext';

/** Shared patient picker used by the doctor, caregiver and reviewer views. */
export function PatientSelector({
  patients = [],
  selectedId,
  onSelect,
  title = 'Select a patient',
  subtitle,
  multi = false,
  selectedIds = [],
  onToggle,
}) {
  const t = useT();
  if (!patients.length) {
    return (
      <section className="card">
        <div className="card-body">
          <EmptyState
            icon="👥"
            title="No patients available"
            message="You will see a patient here once there is a care relationship and the patient has granted consent."
          />
        </div>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t(title)}
          {subtitle && <span className="card-sub">{t(subtitle)}</span>}
        </h3>
      </div>
      <div className="card-body stack">
        {patients.map((patient) => {
          const selected = multi
            ? selectedIds.includes(patient.id)
            : selectedId === patient.id;
          return (
            <button
              key={patient.id}
              type="button"
              className={`radio-option${selected ? ' selected' : ''}`}
              onClick={() => (multi ? onToggle(patient.id) : onSelect(patient.id))}
              style={{ width: '100%', textAlign: 'left', font: 'inherit' }}
            >
              <span
                aria-hidden="true"
                style={{ fontSize: '1.2rem', marginTop: 2 }}
              >
                {selected ? '☑' : '☐'}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span className="opt-title">
                  {patient.full_name}
                  {patient.room_number
                    ? ` · ${t('Room {room}', { room: patient.room_number })}`
                    : ''}
                </span>
                <span className="opt-sub">
                  {[
                    patient.age ? t('{age} years', { age: patient.age }) : null,
                    patient.gender,
                    patient.blood_group,
                    patient.relationship,
                    patient.old_age_home,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              </span>
              {patient.alerts > 0 && (
                <Badge tone="warn">
                  {t('{count} alert', { count: patient.alerts })}
                </Badge>
              )}
              {patient.has_pending_verification && (
                <Badge tone="danger">{t('Verification pending')}</Badge>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default PatientSelector;
