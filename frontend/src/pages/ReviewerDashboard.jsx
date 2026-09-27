import { useCallback, useEffect, useState } from 'react';
import DashboardShell from '../components/common/DashboardShell';
import { PageHeader } from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import EmptyState, { ErrorState } from '../components/common/EmptyState';
import PatientSelector from '../components/caregiver/PatientSelector';
import VerificationQueue from '../components/reviewer/VerificationQueue';
import OCRVerification from '../components/reviewer/OCRVerification';
import MedicationOverview from '../components/reviewer/MedicationOverview';
import MedicationHistory from '../components/reviewer/MedicationHistory';
import MedicationInsights from '../components/reviewer/MedicationInsights';
import RoleChatbot from '../components/chatbot/RoleChatbot';
import reviewerAgent from '../agents/reviewerAgent';
import { useToast } from '../components/common/Toast';
import { reviewerService } from '../services/roleServices';
import { useT } from '../i18n/LanguageContext';

const SECTIONS = [
  {
    items: [
      { key: 'queue', label: 'Verification Queue', icon: '📥' },
      { key: 'lowconf', label: 'Low-Confidence Review', icon: '🔍' },
    ],
  },
  {
    title: 'Patient medication',
    items: [
      { key: 'patients', label: 'Patients', icon: '👥' },
      { key: 'medications', label: 'Medication Overview', icon: '💊' },
      { key: 'history', label: 'Medication History', icon: '🕒' },
    ],
  },
  {
    title: 'Analysis',
    items: [
      { key: 'insights', label: 'Medication Insights', icon: '📈' },
      { key: 'chat', label: 'Medication Memory AI', icon: '💬' },
    ],
  },
];

export function ReviewerDashboard({ user, onSignOut }) {
  const t = useT();
  const toast = useToast();
  const [active, setActive] = useState('queue');
  const [status, setStatus] = useState('PENDING_VERIFICATION');
  const [queue, setQueue] = useState([]);
  const [stats, setStats] = useState({ pending: 0, high_priority: 0 });
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');
  const [taskId, setTaskId] = useState(null);

  const [patients, setPatients] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [medications, setMedications] = useState(null);

  const loadQueue = useCallback(() => {
    setState('loading');
    reviewerService
      .queue(status)
      .then((data) => {
        setQueue(data.queue || []);
        setStats(data.stats || {});
        setState('ready');
      })
      .catch((err) => {
        setError(err.message);
        setState('error');
      });
  }, [status]);

  useEffect(loadQueue, [loadQueue]);

  useEffect(() => {
    reviewerService
      .patients()
      .then((data) => {
        setPatients(data.patients || []);
        if (!selectedId && data.patients?.length) setSelectedId(data.patients[0].id);
      })
      .catch(() => setPatients([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setMedications(null);
    reviewerService
      .medications(selectedId)
      .then(setMedications)
      .catch((err) => toast.error(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const lowConfidence = queue.filter((item) => item.priority === 'HIGH');
  const selected = patients.find((patient) => patient.id === selectedId);

  const sections = SECTIONS.map((section) => ({
    ...section,
    items: section.items.map((item) => {
      if (item.key === 'queue' && stats.pending) return { ...item, count: stats.pending };
      if (item.key === 'lowconf' && stats.high_priority) {
        return { ...item, count: stats.high_priority };
      }
      return item;
    }),
  }));

  const refreshAll = () => {
    loadQueue();
    if (selectedId) {
      reviewerService.medications(selectedId).then(setMedications).catch(() => {});
    }
  };

  return (
    <DashboardShell
      user={user}
      meta={user.extra?.organisation_name}
      sections={sections}
      active={active}
      onSelect={setActive}
      title={t('Medication Verification')}
      subtitle={t('{pending} pending · {high} high priority', {
        pending: stats.pending || 0,
        high: stats.high_priority || 0,
      })}
      onSignOut={onSignOut}
    >
      {active === 'queue' && (
        <div className="stack">
          <PageHeader
            icon="📥"
            title={t('Verification Queue')}
            subtitle={t(
              'You do not receive every medical record. Only clinically important fields read below the auto-accept threshold — medication names, doses, frequencies, prescription instructions, medication changes, allergies and critical instructions — arrive here.',
            )}
          />
          {state === 'loading' && <LoadingState message={t('Loading the queue…')} />}
          {state === 'error' && <ErrorState message={error} onRetry={loadQueue} />}
          {state === 'ready' && (
            <VerificationQueue
              queue={queue}
              status={status}
              onStatus={setStatus}
              onOpen={(item) => setTaskId(item.id)}
            />
          )}
        </div>
      )}

      {active === 'lowconf' && (
        <div className="stack">
          <PageHeader
            icon="🔍"
            title={t('Low-Confidence Medical Data Review')}
            subtitle={t(
              "Readings below 60% confidence. These are the highest-risk extractions in the system — a misread dose or drug name would otherwise flow straight into the patient's health memory.",
            )}
          />
          {lowConfidence.length === 0 ? (
            <EmptyState
              icon="🟢"
              title={t('No high-priority items')}
              message={t('Nothing is currently below the low-confidence threshold.')}
            />
          ) : (
            <VerificationQueue
              queue={lowConfidence}
              status={status}
              onStatus={setStatus}
              onOpen={(item) => setTaskId(item.id)}
            />
          )}
        </div>
      )}

      {active === 'patients' && (
        <div className="stack">
          <PageHeader
            icon="👥"
            title={t('Patients')}
            subtitle={t(
              'Patients who have granted medication consent to reviewers, or who have work in the verification queue.',
            )}
          />
          <PatientSelector
            patients={patients}
            selectedId={selectedId}
            onSelect={(id) => {
              setSelectedId(id);
              setActive('medications');
            }}
            title={t('Select a patient')}
          />
        </div>
      )}

      {active === 'medications' && (
        <div className="stack">
          <PageHeader
            icon="💊"
            title={t('Medication Overview')}
            subtitle={
              selected
                ? t(
                    'Complete medication record for {name}, with source and verification status.',
                    { name: selected.full_name },
                  )
                : t('Select a patient to view their medication record.')
            }
          />
          {!selected && (
            <EmptyState
              icon="👥"
              title={t('No patient selected')}
              action={
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setActive('patients')}
                >
                  {t('Select a patient')}
                </button>
              }
            />
          )}
          {selected && !medications && <LoadingState message={t('Loading medications…')} />}
          {selected && medications && <MedicationOverview data={medications} />}
        </div>
      )}

      {active === 'history' && (
        <div className="stack">
          <PageHeader
            icon="🕒"
            title={t('Medication History')}
            subtitle={
              selected
                ? t('Every medication event recorded for {name}.', {
                    name: selected.full_name,
                  })
                : t('Select a patient first.')
            }
          />
          {selected && !medications && <LoadingState message={t('Loading history…')} />}
          {selected && medications && (
            <MedicationHistory events={medications.medication_history} />
          )}
        </div>
      )}

      {active === 'insights' && (
        <div className="stack">
          <PageHeader
            icon="📈"
            title={t('Medication Insights')}
            subtitle={t(
              'How much verification work the pipeline is creating, and where it comes from.',
            )}
          />
          <MedicationInsights />
        </div>
      )}

      {active === 'chat' && (
        <div className="stack">
          <PageHeader
            icon="💬"
            title={t('Medication Memory Assistant')}
            subtitle={t(
              'Medication-focused retrieval with direct access to the verification queue and OCR readings.',
            )}
          />
          {selected ? (
            <RoleChatbot
              agent={reviewerAgent}
              patientId={selectedId}
              patientName={selected.full_name}
            />
          ) : (
            <EmptyState
              icon="👥"
              title={t('Select a patient')}
              message={t(
                "The assistant answers about one patient's medication memory at a time.",
              )}
              action={
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setActive('patients')}
                >
                  {t('Select a patient')}
                </button>
              }
            />
          )}
        </div>
      )}

      <OCRVerification
        taskId={taskId}
        open={Boolean(taskId)}
        onClose={() => setTaskId(null)}
        onResolved={refreshAll}
      />
    </DashboardShell>
  );
}

export default ReviewerDashboard;
