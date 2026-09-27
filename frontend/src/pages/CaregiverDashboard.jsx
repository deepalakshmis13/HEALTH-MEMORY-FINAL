import { useCallback, useEffect, useMemo, useState } from 'react';
import DashboardShell from '../components/common/DashboardShell';
import { PageHeader, SectionCard } from '../components/common/PageHeader';
import LoadingState from '../components/common/LoadingState';
import EmptyState, { ErrorState } from '../components/common/EmptyState';
import StatCard from '../components/common/StatCard';
import { Badge } from '../components/common/StatusBadge';
import CareTypeSelector from '../components/caregiver/CareTypeSelector';
import ShiftSelector from '../components/caregiver/ShiftSelector';
import PatientSelector from '../components/caregiver/PatientSelector';
import MedicationVerification from '../components/caregiver/MedicationVerification';
import CareTasks from '../components/caregiver/CareTasks';
import InsightFeed from '../components/caregiver/InsightFeed';
import ShiftHandover from '../components/caregiver/ShiftHandover';
import HealthOverview from '../components/health-memory/HealthOverview';
import RoleChatbot from '../components/chatbot/RoleChatbot';
import caregiverAgent from '../agents/caregiverAgent';
import { useToast } from '../components/common/Toast';
import { caregiverService } from '../services/roleServices';
import { OBSERVATION_CATEGORIES } from '../utils/constants';
import { formatDateTime } from '../utils/formatters';
import { useT } from '../i18n/LanguageContext';

const SECTIONS = [
  {
    items: [
      { key: 'setup', label: 'Care Type & Shift', icon: '⚙️' },
      { key: 'medication', label: 'Medication Administration', icon: '💊' },
      { key: 'tasks', label: 'Daily Care Tasks', icon: '✅' },
      { key: 'observations', label: 'Record Observation', icon: '👁' },
    ],
  },
  {
    title: 'Context',
    items: [
      { key: 'patient', label: 'Patient Health Overview', icon: '🩺' },
      { key: 'insights', label: 'Caregiver Insight Feed', icon: '📣' },
      { key: 'alerts', label: 'Alerts', icon: '⚠️' },
    ],
  },
  {
    title: 'End of shift',
    items: [
      { key: 'handover', label: 'Shift Handover AI', icon: '📋' },
      { key: 'chat', label: 'Care Companion AI', icon: '💬' },
    ],
  },
];

export function CaregiverDashboard({ user, onSignOut }) {
  const t = useT();
  const toast = useToast();
  const [active, setActive] = useState('setup');
  const [config, setConfig] = useState(null);
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');

  const [careType, setCareType] = useState('INDIVIDUAL');
  const [facilityId, setFacilityId] = useState(null);
  const [shiftCode, setShiftCode] = useState('MORNING');
  const [selectedIds, setSelectedIds] = useState([]);

  const [shiftDetail, setShiftDetail] = useState(null);
  const [activePatientId, setActivePatientId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [starting, setStarting] = useState(false);

  const [observation, setObservation] = useState({
    category: 'general',
    observation: '',
    severity: 'normal',
  });
  const [savingObservation, setSavingObservation] = useState(false);

  const load = useCallback(() => {
    setState('loading');
    caregiverService
      .config()
      .then((data) => {
        setConfig(data);
        setCareType(data.caregiver.care_type || 'INDIVIDUAL');
        setFacilityId(data.caregiver.old_age_home_id || null);
        if (data.active_shift) {
          setShiftCode(data.active_shift.shift_code);
          setSelectedIds(data.active_shift.assigned_patient_ids || []);
        } else if (data.patients.length) {
          setSelectedIds([data.patients[0].id]);
        }
        setState('ready');
      })
      .catch((err) => {
        setError(err.message);
        setState('error');
      });
  }, []);

  useEffect(load, [load]);

  const activeShiftId = config?.active_shift?.id;

  const loadShift = useCallback(() => {
    if (!activeShiftId) {
      setShiftDetail(null);
      return;
    }
    caregiverService
      .shift(activeShiftId)
      .then((data) => {
        setShiftDetail(data);
        if (!activePatientId && data.patients.length) {
          setActivePatientId(data.patients[0].patient.id);
        }
      })
      .catch((err) => toast.error(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeShiftId, refreshKey]);

  useEffect(loadShift, [loadShift]);

  const startShift = async () => {
    if (careType === 'OLD_AGE_HOME' && !facilityId) {
      toast.warning(t('Choose the facility you are working in.'));
      return;
    }
    if (!selectedIds.length) {
      toast.warning(t('Select at least one patient for this shift.'));
      return;
    }
    setStarting(true);
    try {
      const result = await caregiverService.startShift({
        careType,
        shiftCode,
        facilityId,
        patientIds: selectedIds,
      });
      setConfig((current) => ({ ...current, active_shift: result.shift }));
      setActivePatientId(result.patients[0]);
      setRefreshKey((value) => value + 1);
      setActive('medication');
      toast.success(
        t('{code} shift started with {count} patient(s).', {
          code: result.shift.shift_code,
          count: result.patients.length,
        }),
        t('Shift started'),
      );
    } catch (err) {
      toast.error(err.message, t('Unable to start the shift'));
    } finally {
      setStarting(false);
    }
  };

  const saveObservation = async () => {
    if (!observation.observation.trim() || !activePatientId) return;
    setSavingObservation(true);
    try {
      const result = await caregiverService.addObservation({
        patient_id: activePatientId,
        shift_id: activeShiftId || null,
        category: observation.category,
        observation: observation.observation.trim(),
        severity: observation.severity,
      });
      toast.success(result.message, t('Observation saved'));
      setObservation({ category: 'general', observation: '', severity: 'normal' });
      setRefreshKey((value) => value + 1);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSavingObservation(false);
    }
  };

  const activePatientBlock = useMemo(
    () =>
      shiftDetail?.patients?.find(
        (block) => block.patient.id === activePatientId,
      ) || shiftDetail?.patients?.[0],
    [shiftDetail, activePatientId],
  );

  const shiftPatients =
    shiftDetail?.patients?.map((block) => ({
      id: block.patient.id,
      full_name: block.patient.full_name,
      age: block.patient.age,
      room_number: block.patient.room_number,
      alerts: block.alerts.length,
    })) || [];

  const pendingDoses =
    shiftDetail?.patients?.reduce(
      (total, block) =>
        total +
        block.administrations.filter((item) => item.status === 'Pending').length,
      0,
    ) || 0;

  const allAlerts =
    shiftDetail?.patients?.flatMap((block) =>
      block.alerts.map((alert) => ({ ...alert, patient: block.patient.full_name })),
    ) || [];

  const sections = SECTIONS.map((section) => ({
    ...section,
    items: section.items.map((item) => {
      if (item.key === 'medication' && pendingDoses) {
        return { ...item, count: pendingDoses };
      }
      if (item.key === 'alerts' && allAlerts.length) {
        return { ...item, count: allAlerts.length };
      }
      return item;
    }),
  }));

  if (state === 'loading') {
    return (
      <div className="page">
        <LoadingState message="Loading your care setup…" />
      </div>
    );
  }
  if (state === 'error') {
    return (
      <div className="page">
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const needsShift = !config.active_shift;

  return (
    <DashboardShell
      user={user}
      meta={
        careType === 'OLD_AGE_HOME'
          ? config.caregiver.old_age_home || t('Old age home')
          : t('Individual caregiver')
      }
      sections={sections}
      active={active}
      onSelect={setActive}
      title="Care Dashboard"
      subtitle={
        config.active_shift
          ? t('{code} shift · {start}–{end}', {
              code: config.active_shift.shift_code,
              start: config.active_shift.start_time,
              end: config.active_shift.end_time,
            })
          : 'No active shift'
      }
      onSignOut={onSignOut}
      topbarActions={
        config.active_shift && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setActive('handover')}
          >
            📋 {t('Handover')}
          </button>
        )
      }
    >
      {active === 'setup' && (
        <div className="stack">
          <PageHeader
            icon="⚙️"
            title="Care Type & Shift"
            subtitle="Choose the setting you are working in. This changes the whole workflow: one patient at home, or a facility with shift-based rounds."
          />

          <div className="grid grid-2">
            <CareTypeSelector
              value={careType}
              onChange={setCareType}
              facilities={config.facilities}
              facilityId={facilityId}
              onFacility={setFacilityId}
            />
            {careType === 'OLD_AGE_HOME' ? (
              <ShiftSelector
                shifts={config.shifts}
                value={shiftCode}
                onChange={setShiftCode}
                activeShift={config.active_shift}
              />
            ) : (
              <SectionCard
                title="Individual care"
                subtitle="One patient, one continuous care record"
              >
                <p className="muted">
                  {t(
                    "In individual mode you work with a single patient: today's care plan, medication, observations and alerts. A shift is still recorded so the handover stays consistent.",
                  )}
                </p>
                <div className="field mt-2">
                  <label htmlFor="ind-shift">{t('Shift period')}</label>
                  <select
                    id="ind-shift"
                    value={shiftCode}
                    onChange={(event) => setShiftCode(event.target.value)}
                  >
                    {config.shifts.map((shift) => (
                      <option key={shift.id} value={shift.id}>
                        {t(shift.label)} ({shift.start}–{shift.end})
                      </option>
                    ))}
                  </select>
                </div>
              </SectionCard>
            )}
          </div>

          <PatientSelector
            patients={config.patients}
            multi={careType === 'OLD_AGE_HOME'}
            selectedIds={selectedIds}
            selectedId={selectedIds[0]}
            onSelect={(id) => setSelectedIds([id])}
            onToggle={(id) =>
              setSelectedIds((current) =>
                current.includes(id)
                  ? current.filter((value) => value !== id)
                  : [...current, id],
              )
            }
            title={
              careType === 'OLD_AGE_HOME'
                ? 'Residents assigned to this shift'
                : 'Patient in your care'
            }
            subtitle="Only patients you are assigned to, and who have granted consent"
          />

          <div className="row">
            <button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={startShift}
              disabled={starting}
            >
              {starting
                ? t('Starting shift…')
                : config.active_shift
                  ? t('Start a new shift')
                  : t('Start shift')}
            </button>
            {config.active_shift && (
              <span className="muted small">
                {t('Active shift started {time}', {
                  time: formatDateTime(config.active_shift.created_at),
                })}
              </span>
            )}
          </div>
        </div>
      )}

      {active !== 'setup' && needsShift && (
        <EmptyState
          icon="⏱"
          title="No active shift"
          message="Choose your care setting and shift to begin. Medication rounds and care tasks are generated from the shift hours."
          action={
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setActive('setup')}
            >
              {t('Set up my shift')}
            </button>
          }
        />
      )}

      {!needsShift && active !== 'setup' && (
        <>
          {shiftPatients.length > 1 && (
            <div className="row mb-2">
              <span className="small muted">{t('Resident:')}</span>
              {shiftPatients.map((patient) => (
                <button
                  key={patient.id}
                  type="button"
                  className={`chip${activePatientId === patient.id ? ' active' : ''}`}
                  onClick={() => setActivePatientId(patient.id)}
                >
                  {patient.full_name}
                  {patient.room_number ? ` · ${patient.room_number}` : ''}
                </button>
              ))}
            </div>
          )}

          {active === 'medication' && (
            <div className="stack">
              <PageHeader
                icon="💊"
                title="Medication Administration Verification"
                subtitle="Each dose you record becomes a permanent, attributed entry in the patient's health memory."
              />
              <div className="grid grid-4">
                <StatCard
                  icon="⏰"
                  label={t('Doses pending')}
                  value={
                    activePatientBlock?.administrations.filter(
                      (item) => item.status === 'Pending',
                    ).length || 0
                  }
                  tone="warn"
                />
                <StatCard
                  icon="✅"
                  label={t('Administered')}
                  value={
                    activePatientBlock?.administrations.filter(
                      (item) => item.status === 'Administered',
                    ).length || 0
                  }
                  tone="ok"
                />
                <StatCard
                  icon="⚠️"
                  label={t('Needs attention')}
                  value={
                    activePatientBlock?.administrations.filter((item) =>
                      ['Missed', 'Needs Attention'].includes(item.status),
                    ).length || 0
                  }
                  tone="danger"
                />
                <StatCard
                  icon="🔍"
                  label={t('Unverified medicines')}
                  value={
                    activePatientBlock?.medications.filter(
                      (medication) =>
                        medication.verification_status === 'PENDING_VERIFICATION',
                    ).length || 0
                  }
                  tone="warn"
                  hint={t('Do not administer')}
                />
              </div>
              <SectionCard
                title={t('Medication round — {name}', {
                  name: activePatientBlock?.patient.full_name || '',
                })}
                subtitle={t('{code} shift · {start}–{end}', {
                  code: config.active_shift.shift_code,
                  start: config.active_shift.start_time,
                  end: config.active_shift.end_time,
                })}
                flush
              >
                <div style={{ padding: 0 }}>
                  <MedicationVerification
                    patient={activePatientBlock?.patient}
                    administrations={activePatientBlock?.administrations || []}
                    onDone={() => setRefreshKey((value) => value + 1)}
                  />
                </div>
              </SectionCard>
            </div>
          )}

          {active === 'tasks' && (
            <div className="stack">
              <PageHeader
                icon="✅"
                title="Daily Care Tasks"
                subtitle="Routine care for the hours covered by this shift."
              />
              <SectionCard
                title={activePatientBlock?.patient.full_name}
                subtitle="Mark each task as it is completed"
              >
                <CareTasks
                  tasks={activePatientBlock?.tasks || []}
                  onDone={() => setRefreshKey((value) => value + 1)}
                />
              </SectionCard>
            </div>
          )}

          {active === 'observations' && (
            <div className="stack">
              <PageHeader
                icon="👁"
                title="Record an observation"
                subtitle="What you notice during care becomes part of the longitudinal record the doctor sees."
              />
              <div className="grid grid-2">
                <SectionCard title="New observation">
                  <div className="field">
                    <label htmlFor="obs-category">{t('Category')}</label>
                    <select
                      id="obs-category"
                      value={observation.category}
                      onChange={(event) =>
                        setObservation((current) => ({
                          ...current,
                          category: event.target.value,
                        }))
                      }
                    >
                      {OBSERVATION_CATEGORIES.map((category) => (
                        <option key={category.key} value={category.key}>
                          {t(category.label)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="obs-text">{t('What did you observe?')}</label>
                    <textarea
                      id="obs-text"
                      value={observation.observation}
                      onChange={(event) =>
                        setObservation((current) => ({
                          ...current,
                          observation: event.target.value,
                        }))
                      }
                      rows={4}
                      placeholder={t(
                        'e.g. Complained of dizziness at 09:15 while getting out of bed.',
                      )}
                    />
                  </div>
                  <div className="field">
                    <span className="form-label">{t('Priority')}</span>
                    <div className="row tight">
                      {['normal', 'attention', 'critical'].map((severity) => (
                        <button
                          key={severity}
                          type="button"
                          className={`chip${
                            observation.severity === severity ? ' active' : ''
                          }`}
                          onClick={() =>
                            setObservation((current) => ({ ...current, severity }))
                          }
                        >
                          {t(severity)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={saveObservation}
                    disabled={savingObservation || !observation.observation.trim()}
                  >
                    {savingObservation ? t('Saving…') : t('Save observation')}
                  </button>
                </SectionCard>

                <SectionCard
                  title="This shift's observations"
                  subtitle={activePatientBlock?.patient.full_name}
                >
                  {activePatientBlock?.observations?.length ? (
                    <div className="stack">
                      {activePatientBlock.observations.map((item) => (
                        <div className="row between" key={item.id}>
                          <div>
                            <div>{item.observation}</div>
                            <div className="tiny faint">
                              {item.observed_at_label} · {t(item.category)}
                            </div>
                          </div>
                          <Badge
                            tone={item.severity === 'normal' ? 'outline' : 'warn'}
                          >
                            {t(item.severity)}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">
                      {t('Nothing recorded yet in this shift.')}
                    </p>
                  )}
                </SectionCard>
              </div>
            </div>
          )}

          {active === 'patient' && (
            <div className="stack">
              <PageHeader
                icon="🩺"
                title="Patient Health Overview"
                subtitle="Only what the patient has shared with caregivers."
              />
              <HealthOverview
                data={{
                  patient: activePatientBlock?.patient,
                  counts: {},
                  medications: activePatientBlock?.medications || [],
                  allergies: activePatientBlock?.allergies || [],
                  conditions: [],
                  lab_results: [],
                  hospital_visits: [],
                  alerts: activePatientBlock?.alerts || [],
                }}
              />
            </div>
          )}

          {active === 'insights' && (
            <div className="stack">
              <PageHeader
                icon="📣"
                title="Caregiver Insight Feed"
                subtitle="What has been reported and observed recently, across the patients in your care."
              />
              <InsightFeed patientId={activePatientId} refreshKey={refreshKey} />
            </div>
          )}

          {active === 'alerts' && (
            <div className="stack">
              <PageHeader
                icon="⚠️"
                title="Alerts"
                subtitle="Anything needing attention across the patients in this shift."
              />
              {allAlerts.length === 0 ? (
                <EmptyState
                  icon="🟢"
                  title="No alerts"
                  message="Nothing needs escalation right now. Continue the routine care plan."
                />
              ) : (
                <div className="stack">
                  {allAlerts.map((alert, index) => (
                    <div
                      key={index}
                      className={`alert alert-${
                        alert.level === 'critical' ? 'danger' : 'warn'
                      }`}
                    >
                      <span className="alert-icon" aria-hidden="true">
                        {alert.level === 'critical' ? '🚨' : '⚠️'}
                      </span>
                      <div className="alert-body">
                        <div className="alert-title">
                          {alert.patient} — {alert.title}
                        </div>
                        {alert.detail}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {active === 'handover' && (
            <div className="stack">
              <PageHeader
                icon="📋"
                title="Shift Handover"
                subtitle="Generate the handover for the next shift from this shift's authorized records, then review it before saving."
              />
              <ShiftHandover
                shift={config.active_shift}
                patientIds={config.active_shift.assigned_patient_ids}
                onSaved={() => setRefreshKey((value) => value + 1)}
              />
            </div>
          )}

          {active === 'chat' && (
            <div className="stack">
              <PageHeader
                icon="💬"
                title="Care Companion"
                subtitle="Ask what is due, what happened in the previous shift, and what to watch for."
              />
              <RoleChatbot
                agent={caregiverAgent}
                patientId={activePatientId}
                patientName={activePatientBlock?.patient.full_name}
                shiftId={activeShiftId}
              />
            </div>
          )}
        </>
      )}
    </DashboardShell>
  );
}

export default CaregiverDashboard;
