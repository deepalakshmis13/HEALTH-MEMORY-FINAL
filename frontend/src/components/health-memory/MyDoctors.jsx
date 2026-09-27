import { useCallback, useEffect, useState } from 'react';
import { SectionCard } from '../common/PageHeader';
import LoadingState from '../common/LoadingState';
import EmptyState, { ErrorState } from '../common/EmptyState';
import { Badge } from '../common/StatusBadge';
import { useToast } from '../common/Toast';
import { careTeamService } from '../../services/roleServices';
import { formatDate } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

/**
 * The patient's control over which doctors treat them.
 *
 * A patient may have several doctors at once. Adding one makes the patient
 * appear on that doctor's dashboard; removing one takes the patient off it
 * while keeping every past visit, prescription, medicine and test result
 * exactly as it was. Doctors cannot add or remove themselves — this screen is
 * the only way the relationship changes.
 */
export function MyDoctors({ patientId, onChanged }) {
  const t = useT();
  const toast = useToast();
  const [team, setTeam] = useState(null);
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [working, setWorking] = useState(0);

  const load = useCallback(
    (silent = false) => {
      if (!silent) setState('loading');
      careTeamService
        .list(patientId)
        .then((data) => {
          setTeam(data);
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
    load();
  }, [load]);

  const runSearch = (event) => {
    event.preventDefault();
    setSearching(true);
    careTeamService
      .search(query, patientId)
      .then((data) => setResults(data.results || []))
      .catch((err) => toast.error(err.message))
      .finally(() => setSearching(false));
  };

  const after = (message) => {
    toast.success(message);
    load(true);
    setResults(null);
    setQuery('');
    if (onChanged) onChanged();
  };

  const add = (doctorId, makePrimary = false) => {
    setWorking(doctorId);
    careTeamService
      .add(patientId, doctorId, makePrimary)
      .then((data) => after(data.message))
      .catch((err) => toast.error(err.message))
      .finally(() => setWorking(0));
  };

  const remove = (doctor) => {
    const confirmed = window.confirm(
      t(
        'Remove {name} from your doctors? They will no longer see your health memory. Your past visits, medicines and reports are kept.',
        { name: doctor.name },
      ),
    );
    if (!confirmed) return;
    setWorking(doctor.id);
    careTeamService
      .remove(patientId, doctor.id)
      .then((data) => after(data.message))
      .catch((err) => toast.error(err.message))
      .finally(() => setWorking(0));
  };

  const makePrimary = (doctor) => {
    setWorking(doctor.id);
    careTeamService
      .setPrimary(patientId, doctor.id)
      .then((data) => after(data.message))
      .catch((err) => toast.error(err.message))
      .finally(() => setWorking(0));
  };

  if (state === 'loading') return <LoadingState message={t('Loading your doctors…')} />;
  if (state === 'error') return <ErrorState message={error} onRetry={load} />;

  const { doctors = [], suggested = [], past_doctors: past = [] } = team || {};

  return (
    <div className="stack">
      <SectionCard
        title="My Doctors"
        subtitle={t('{count} doctor(s) can see your health memory', {
          count: doctors.length,
        })}
        flush={doctors.length > 0}
      >
        {doctors.length === 0 ? (
          <EmptyState
            icon="🩺"
            title={t('You have not added a doctor yet')}
            message={t(
              'Search below and add your doctor. Only you can decide who sees your health memory.',
            )}
          />
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t('Doctor')}</th>
                  <th>{t('Specialty')}</th>
                  <th>{t('Hospital / Clinic')}</th>
                  <th>{t('Added on')}</th>
                  <th>{t('Actions')}</th>
                </tr>
              </thead>
              <tbody>
                {doctors.map((doctor) => (
                  <tr key={doctor.id}>
                    <td>
                      <span className="strong">{doctor.name}</span>{' '}
                      {doctor.is_primary && (
                        <Badge tone="ok">{t('Primary doctor')}</Badge>
                      )}
                    </td>
                    <td>{doctor.specialty || '—'}</td>
                    <td>{doctor.hospital || '—'}</td>
                    <td>{doctor.added_at ? formatDate(doctor.added_at) : '—'}</td>
                    <td>
                      <div className="row">
                        {!doctor.is_primary && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => makePrimary(doctor)}
                            disabled={working === doctor.id}
                          >
                            {t('Make primary')}
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => remove(doctor)}
                          disabled={working === doctor.id}
                        >
                          {t('Remove')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {suggested.length > 0 && (
        <SectionCard
          title="Doctors found in your records"
          subtitle={t(
            'Named in a document you uploaded. They cannot see anything until you add them.',
          )}
        >
          <div className="stack">
            {suggested.map((doctor) => (
              <div key={doctor.id} className="row between">
                <div>
                  <div className="strong">{doctor.name}</div>
                  <div className="tiny muted">
                    {[doctor.specialty, doctor.hospital].filter(Boolean).join(' · ') ||
                      t('No further details in the record')}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => add(doctor.id)}
                  disabled={working === doctor.id}
                >
                  {t('Add doctor')}
                </button>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      <SectionCard
        title="Add a doctor"
        subtitle={t('Search by name, specialty or hospital')}
      >
        <form onSubmit={runSearch}>
          <div className="row">
            <div className="field" style={{ flex: '1 1 260px' }}>
              <label htmlFor="doctor-search">{t('Find a doctor')}</label>
              <input
                id="doctor-search"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t('For example: Kumar, Cardiology, Apollo')}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={searching}>
              {searching ? t('Searching…') : t('Search')}
            </button>
          </div>
        </form>

        {results !== null && (
          <div className="stack mt-2">
            {results.length === 0 ? (
              <EmptyState
                icon="🔍"
                title={t('No doctor found')}
                message={t(
                  'Try part of the name, the specialty, or the hospital. Only doctors registered on Health Memory can be added.',
                )}
              />
            ) : (
              results.map((doctor) => (
                <div key={doctor.id} className="row between">
                  <div>
                    <div className="strong">{doctor.name}</div>
                    <div className="tiny muted">
                      {[doctor.specialty, doctor.hospital].filter(Boolean).join(' · ') ||
                        t('No further details available')}
                    </div>
                  </div>
                  {doctor.already_added ? (
                    <Badge tone="ok">{t('Already added')}</Badge>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => add(doctor.id)}
                      disabled={working === doctor.id}
                    >
                      {t('Add doctor')}
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </SectionCard>

      {past.length > 0 && (
        <SectionCard
          title="Doctors you have removed"
          subtitle={t('Their past records stay in your health memory')}
        >
          <div className="stack">
            {past.map((doctor) => (
              <div key={doctor.id} className="row between">
                <div>
                  <div className="strong">{doctor.name}</div>
                  <div className="tiny muted">
                    {t('{count} record(s) kept', { count: doctor.records_contributed })}
                    {doctor.removed_at
                      ? ` · ${t('removed {date}', {
                          date: formatDate(doctor.removed_at),
                        })}`
                      : ''}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => add(doctor.id)}
                  disabled={working === doctor.id}
                >
                  {t('Add again')}
                </button>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

export default MyDoctors;
