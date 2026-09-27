import { useCallback, useEffect, useState } from 'react';
import DashboardShell from '../components/common/DashboardShell';
import { PageHeader, SectionCard } from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import EmptyState, { ErrorState } from '../components/common/EmptyState';
import { Badge } from '../components/common/StatusBadge';
import HealthOverview from '../components/health-memory/HealthOverview';
import MemoryTimeline from '../components/health-memory/MemoryTimeline';
import AddHealthData from '../components/health-memory/AddHealthData';
import DocumentUpload from '../components/health-memory/DocumentUpload';
import MyDoctors from '../components/health-memory/MyDoctors';
import ConsentCenter from '../components/consent/ConsentCenter';
import EmergencyCard from '../components/emergency/EmergencyCard';
import EmergencyMode from '../components/emergency/EmergencyMode';
import RoleChatbot from '../components/chatbot/RoleChatbot';
import patientAgent from '../agents/patientAgent';
import memoryService from '../services/memoryService';
import ingestionService from '../services/ingestionService';
import { formatDateTime, percent } from '../utils/formatters';
import { useT } from '../i18n/LanguageContext';

const SECTIONS = [
  {
    items: [
      { key: 'overview', label: 'Health Overview', icon: '🏠' },
      { key: 'timeline', label: 'My Health Memory Timeline', icon: '🕒' },
      { key: 'add', label: 'Add Health Data', icon: '➕' },
    ],
  },
  {
    title: 'My record',
    items: [
      { key: 'documents', label: 'Documents', icon: '📄' },
      { key: 'doctors', label: 'My Doctors', icon: '🩺' },
      { key: 'voice', label: 'Voice Health Diary', icon: '🎙' },
      { key: 'emergency', label: 'Emergency Health Card', icon: '🚨' },
      { key: 'consent', label: 'Consent Control Center', icon: '🔐' },
    ],
  },
  {
    title: 'Assistant',
    items: [{ key: 'chat', label: 'My Health Memory AI', icon: '💬' }],
  },
];

export function PatientDashboard({ user, onSignOut }) {
  const t = useT();
  const patientId = user.patient_id;
  const [active, setActive] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [emergencyCard, setEmergencyCard] = useState(null);
  const [emergencyOpen, setEmergencyOpen] = useState(false);
  const [voiceEntries, setVoiceEntries] = useState(null);

  /**
   * `silent` keeps the dashboard mounted while refetching — otherwise a save
   * would unmount the ingestion flow mid-way and throw away its result screen.
   */
  const load = useCallback(
    (silent = false) => {
      if (!patientId) return;
      if (!silent) setState('loading');
      memoryService
        .overview(patientId)
        .then((data) => {
          setOverview(data);
          setState('ready');
        })
        .catch((err) => {
          setError(err.message);
          setState('error');
        });
    },
    [patientId],
  );

  useEffect(() => {
    load(refreshKey > 0);
  }, [load, refreshKey]);

  useEffect(() => {
    if (!patientId) return;
    memoryService
      .emergencyCard(patientId)
      .then(setEmergencyCard)
      .catch(() => setEmergencyCard(null));
  }, [patientId, refreshKey]);

  useEffect(() => {
    if (active !== 'voice' || !patientId) return;
    ingestionService
      .voiceEntries(patientId)
      .then((data) => setVoiceEntries(data.entries || []))
      .catch(() => setVoiceEntries([]));
  }, [active, patientId, refreshKey]);

  const refresh = () => setRefreshKey((value) => value + 1);
  const isFirstTime = overview?.counts?.memory_events === 0;

  const sections = SECTIONS.map((section) => ({
    ...section,
    items: section.items.map((item) =>
      item.key === 'overview' && overview?.counts?.pending_verification
        ? { ...item, count: overview.counts.pending_verification, muted: true }
        : item,
    ),
  }));

  if (!patientId) {
    return (
      <div className="page">
        <ErrorState message={t('This account is not linked to a patient record.')} />
      </div>
    );
  }

  return (
    <DashboardShell
      user={user}
      meta={
        overview?.patient
          ? t('{age} years · {bloodGroup}', {
              age: overview.patient.age,
              bloodGroup:
                overview.patient.blood_group || t('blood group unknown'),
            })
          : undefined
      }
      sections={sections}
      active={active}
      onSelect={setActive}
      title={t('My Health Memory')}
      subtitle={t('Everything about your health, in one place')}
      onSignOut={onSignOut}
      seniorScale
      topbarActions={
        <button
          type="button"
          className="btn btn-danger btn-sm"
          onClick={() => setEmergencyOpen(true)}
          disabled={!emergencyCard}
        >
          🚨 {t('Emergency')}
        </button>
      }
    >
      {state === 'loading' && <LoadingState message={t('Loading your health memory…')} />}
      {state === 'error' && <ErrorState message={error} onRetry={load} />}

      {state === 'ready' && (
        <>
          {active === 'overview' && (
            <div className="stack">
              <PageHeader
                icon="🏠"
                title={t('Hello, {name}', { name: user.full_name.split(' ')[0] })}
                subtitle={
                  isFirstTime
                    ? t(
                        'Welcome to My Health Memory. Add your first health information to begin.',
                      )
                    : t(
                        'Last updated {date}. Everything here keeps a record of where it came from.',
                        { date: formatDateTime(overview.last_updated) },
                      )
                }
                actions={
                  <button
                    type="button"
                    className="btn btn-primary btn-lg"
                    onClick={() => setActive('add')}
                  >
                    ➕ {t('Add Health Data')}
                  </button>
                }
              />
              {isFirstTime ? (
                <AddHealthData
                  patientId={patientId}
                  firstTime
                  onSaved={refresh}
                />
              ) : (
                <HealthOverview
                  data={overview}
                  plain
                  onAddData={() => setActive('add')}
                />
              )}
            </div>
          )}

          {active === 'timeline' && (
            <div className="stack">
              <PageHeader
                icon="🕒"
                title={t('My Health Memory Timeline')}
                subtitle={t(
                  'Every visit, medicine, test and note — newest first, with the source it came from.',
                )}
              />
              <MemoryTimeline
                patientId={patientId}
                refreshKey={refreshKey}
                emptyAction={
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setActive('add')}
                  >
                    {t('Add health data')}
                  </button>
                }
              />
            </div>
          )}

          {active === 'add' && (
            <AddHealthData
              patientId={patientId}
              onSaved={refresh}
              firstTime={isFirstTime}
            />
          )}

          {active === 'documents' && (
            <div className="stack">
              <PageHeader
                icon="📄"
                title={t('Documents')}
                subtitle={t(
                  'Prescriptions, lab reports and handwritten doctor notes you have added.',
                )}
              />
              <DocumentUpload
                patientId={patientId}
                refreshKey={refreshKey}
                onAddDocument={() => setActive('add')}
              />
            </div>
          )}

          {active === 'doctors' && (
            <div className="stack">
              <PageHeader
                icon="🩺"
                title={t('My Doctors')}
                subtitle={t(
                  'You choose which doctors can see your health memory. Removing a doctor never deletes your records.',
                )}
              />
              <MyDoctors patientId={patientId} onChanged={refresh} />
            </div>
          )}

          {active === 'voice' && (
            <div className="stack">
              <PageHeader
                icon="🎙"
                title={t('Voice Health Diary')}
                subtitle={t(
                  'Everything you have recorded in your own words. Stored as patient-reported information — never as a diagnosis.',
                )}
                actions={
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setActive('add')}
                  >
                    {t('Record a new entry')}
                  </button>
                }
              />
              <SectionCard title={t('Recorded entries')}>
                {voiceEntries === null && <LoadingState message={t('Loading entries…')} />}
                {voiceEntries?.length === 0 && (
                  <EmptyState
                    icon="🎙"
                    title={t('No voice entries yet')}
                    message={t(
                      'Tap Add Health Data and choose VOICE to tell us how you are feeling.',
                    )}
                  />
                )}
                {voiceEntries?.length > 0 && (
                  <div className="stack">
                    {voiceEntries.map((entry) => (
                      <div className="memory-card" key={entry.id}>
                        <div className="memory-card-head">
                          <h4>{entry.recorded_at_label}</h4>
                          <Badge tone="outline">
                            {t('Recognition {value}', {
                              value: percent(entry.confidence),
                            })}
                          </Badge>
                        </div>
                        <div className="memory-card-body">“{entry.transcript}”</div>
                        <div className="memory-card-meta">
                          <Badge tone="outline">🎙 {t('Patient Reported')}</Badge>
                          {entry.duration_seconds && (
                            <span>
                              {t('{seconds}s', {
                                seconds: Math.round(entry.duration_seconds),
                              })}
                            </span>
                          )}
                          {entry.entities?.medications?.length > 0 && (
                            <span>
                              · {t('mentions')}{' '}
                              {entry.entities.medications
                                .map((medication) => medication.name)
                                .join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </SectionCard>
            </div>
          )}

          {active === 'emergency' && (
            <div className="stack">
              <PageHeader
                icon="🚨"
                title={t('Emergency Health Card')}
                subtitle={t('The information a paramedic or a new doctor needs first.')}
                actions={
                  <>
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() => setEmergencyOpen(true)}
                    >
                      {t('Open emergency mode')}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline"
                      onClick={() => window.print()}
                    >
                      🖨 {t('Print')}
                    </button>
                  </>
                }
              />
              {emergencyCard ? (
                <EmergencyCard card={emergencyCard} />
              ) : (
                <LoadingState message={t('Preparing your emergency card…')} />
              )}
            </div>
          )}

          {active === 'consent' && <ConsentCenter patientId={patientId} />}

          {active === 'chat' && (
            <div className="stack">
              <PageHeader
                icon="💬"
                title={t('My Health Memory Assistant')}
                subtitle={t(
                  'Ask about your medicines, your last visit or anything saved in your record. Every answer shows where the information came from.',
                )}
              />
              <RoleChatbot
                agent={patientAgent}
                patientId={patientId}
                patientName={user.full_name}
              />
            </div>
          )}
        </>
      )}

      <EmergencyMode
        card={emergencyCard}
        open={emergencyOpen}
        onClose={() => setEmergencyOpen(false)}
      />
    </DashboardShell>
  );
}

export default PatientDashboard;
