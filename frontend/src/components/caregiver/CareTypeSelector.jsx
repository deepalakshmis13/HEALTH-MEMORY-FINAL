import { useT } from '../../i18n/LanguageContext';

export function CareTypeSelector({ value, onChange, facilities = [], facilityId, onFacility }) {
  const t = useT();
  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Care Type')}
          <span className="card-sub">
            {t('This decides whether you work with one patient or a whole facility')}
          </span>
        </h3>
      </div>
      <div className="card-body">
        <div className="radio-group">
          <label
            className={`radio-option${value === 'INDIVIDUAL' ? ' selected' : ''}`}
          >
            <input
              type="radio"
              name="care-type"
              checked={value === 'INDIVIDUAL'}
              onChange={() => onChange('INDIVIDUAL')}
            />
            <span>
              <span className="opt-title">{t('Individual Caregiver')}</span>
              <span className="opt-sub">
                {t(
                  "One patient at home — today's care, medications, observations, appointments, alerts and handover.",
                )}
              </span>
            </span>
          </label>

          <label
            className={`radio-option${value === 'OLD_AGE_HOME' ? ' selected' : ''}`}
          >
            <input
              type="radio"
              name="care-type"
              checked={value === 'OLD_AGE_HOME'}
              onChange={() => onChange('OLD_AGE_HOME')}
            />
            <span>
              <span className="opt-title">{t('Old Age Home')}</span>
              <span className="opt-sub">
                {t(
                  'Multiple residents, shift-based work, medication rounds and a structured handover to the next shift.',
                )}
              </span>
            </span>
          </label>
        </div>

        {value === 'OLD_AGE_HOME' && facilities.length > 0 && (
          <div className="field mt-2">
            <label htmlFor="facility">{t('Facility')}</label>
            <select
              id="facility"
              value={facilityId || ''}
              onChange={(event) => onFacility(Number(event.target.value))}
            >
              <option value="">{t('Select a facility…')}</option>
              {facilities.map((facility) => (
                <option key={facility.id} value={facility.id}>
                  {facility.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </section>
  );
}

export default CareTypeSelector;
