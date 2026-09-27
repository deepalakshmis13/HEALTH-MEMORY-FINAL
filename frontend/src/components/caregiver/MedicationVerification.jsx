import { useState } from 'react';
import { Badge, VerificationBadge } from '../common/StatusBadge';
import Modal from '../common/Modal';
import EmptyState from '../common/EmptyState';
import { useToast } from '../common/Toast';
import { caregiverService } from '../../services/roleServices';
import { useT } from '../../i18n/LanguageContext';

const STATUS_TONES = {
  Administered: 'ok',
  Pending: 'outline',
  Missed: 'danger',
  Skipped: 'warn',
  Delayed: 'warn',
  'Needs Attention': 'danger',
};

/** Medication administration record — becomes persistent health memory (§27). */
export function MedicationVerification({ patient, administrations = [], onDone }) {
  const t = useT();
  const toast = useToast();
  const [target, setTarget] = useState(null);
  const [status, setStatus] = useState('Administered');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);

  const open = (item) => {
    setTarget(item);
    setStatus(
      item.verification_status === 'PENDING_VERIFICATION' ? 'Needs Attention' : 'Administered',
    );
    setNotes('');
  };

  const submit = async () => {
    if (!target) return;
    setBusy(true);
    try {
      const result = await caregiverService.verifyMedication({
        administration_id: target.id,
        status,
        notes: notes || null,
      });
      toast.success(
        result.message,
        t('{medication} recorded', { medication: target.medication }),
      );
      setTarget(null);
      onDone?.();
    } catch (error) {
      toast.error(error.message, t('Not recorded'));
    } finally {
      setBusy(false);
    }
  };

  if (!administrations.length) {
    return (
      <EmptyState
        icon="💊"
        title="No medication scheduled in this shift"
        message="Doses fall into a shift based on their scheduled times. Nothing is due for this resident during these hours."
      />
    );
  }

  return (
    <>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>{t('Time')}</th>
              <th>{t('Medication')}</th>
              <th>{t('Dose')}</th>
              <th>{t('Prescriber')}</th>
              <th>{t('Status')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {administrations.map((item) => (
              <tr key={item.id}>
                <td className="strong nowrap">{item.scheduled_time}</td>
                <td>
                  <div className="strong">{item.medication}</div>
                  {item.verification_status === 'PENDING_VERIFICATION' && (
                    <VerificationBadge status={item.verification_status} />
                  )}
                </td>
                <td>
                  {item.dose || '—'}
                  <div className="tiny faint">{item.frequency}</div>
                </td>
                <td className="small muted">{item.prescriber || '—'}</td>
                <td>
                  <Badge tone={STATUS_TONES[item.status] || 'outline'}>
                    {t(item.status)}
                  </Badge>
                  {item.notes && <div className="tiny faint">{item.notes}</div>}
                </td>
                <td className="right">
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => open(item)}
                  >
                    {t('Verify Administration')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        open={Boolean(target)}
        title={t('Verify administration — {medication}', {
          medication: target?.medication || '',
        })}
        onClose={() => setTarget(null)}
        footer={
          <>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => setTarget(null)}
            >
              {t('Cancel')}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={submit}
              disabled={busy}
            >
              {busy ? t('Recording…') : t('Record in health memory')}
            </button>
          </>
        }
      >
        {target?.verification_status === 'PENDING_VERIFICATION' && (
          <div className="alert alert-danger mb-2">
            <span className="alert-icon" aria-hidden="true">
              ⛔
            </span>
            <div className="alert-body">
              <div className="alert-title">{t('Do not administer')}</div>
              {t(
                'This medication came from a low-confidence document reading and is still awaiting reviewer verification. It cannot be recorded as administered.',
              )}
            </div>
          </div>
        )}

        <div className="kv-list mb-2">
          <div className="kv">
            <span className="kv-key">{t('Patient')}</span>
            <span className="kv-val">{patient?.full_name}</span>
          </div>
          <div className="kv">
            <span className="kv-key">{t('Medication')}</span>
            <span className="kv-val">
              {target?.medication} {target?.dose}
            </span>
          </div>
          <div className="kv">
            <span className="kv-key">{t('Scheduled')}</span>
            <span className="kv-val">{target?.scheduled_time}</span>
          </div>
          <div className="kv">
            <span className="kv-key">{t('Prescriber')}</span>
            <span className="kv-val">{target?.prescriber || t('not recorded')}</span>
          </div>
        </div>

        <div className="field">
          <label htmlFor="admin-status">{t('Status')}</label>
          <select
            id="admin-status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {['Administered', 'Missed', 'Skipped', 'Delayed', 'Needs Attention'].map(
              (option) => (
                <option key={option} value={option}>
                  {t(option)}
                </option>
              ),
            )}
          </select>
        </div>

        <div className="field">
          <label htmlFor="admin-notes">{t('Notes (optional)')}</label>
          <textarea
            id="admin-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            placeholder={t(
              'e.g. taken with breakfast, refused, or vomited afterwards',
            )}
          />
        </div>

        <p className="tiny faint">
          {t(
            "This is written to the patient's health memory as a caregiver-recorded event, with your name, the shift and the time.",
          )}
        </p>
      </Modal>
    </>
  );
}

export default MedicationVerification;
