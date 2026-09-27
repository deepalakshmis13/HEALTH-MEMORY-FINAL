import { Badge } from '../common/StatusBadge';
import { useT } from '../../i18n/LanguageContext';

export function ShiftSelector({ shifts = [], value, onChange, activeShift }) {
  const t = useT();
  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Shift Management')}
          <span className="card-sub">
            {t('Shift times are configurable in the platform settings')}
          </span>
        </h3>
        {activeShift && (
          <Badge tone="ok">
            {t('Active: {code} · {start}–{end}', {
              code: activeShift.shift_code,
              start: activeShift.start_time,
              end: activeShift.end_time,
            })}
          </Badge>
        )}
      </div>
      <div className="card-body">
        <div className="radio-group">
          {shifts.map((shift) => (
            <label
              key={shift.id}
              className={`radio-option${value === shift.id ? ' selected' : ''}`}
            >
              <input
                type="radio"
                name="shift"
                checked={value === shift.id}
                onChange={() => onChange(shift.id)}
              />
              <span>
                <span className="opt-title">{t(shift.label)}</span>
                <span className="opt-sub">
                  {shift.start} – {shift.end}
                </span>
              </span>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}

export default ShiftSelector;
