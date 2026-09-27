import {
  HIGH_CONFIDENCE_THRESHOLD,
  MEDIUM_CONFIDENCE_THRESHOLD,
} from '../../utils/constants';
import { confidenceBand, percent } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

const NOTES = {
  high: 'At or above {high}% — accepted into health memory.',
  medium: 'Between {medium}% and {high}% — needs verification if clinically important.',
  low: 'Below {medium}% — high priority verification.',
  unknown: 'No confidence score recorded.',
};

export function ConfidenceIndicator({ value, label = 'Confidence', showNote = false }) {
  const t = useT();
  const band = confidenceBand(value);
  const width = value === null || value === undefined ? 0 : Math.round(value * 100);
  return (
    <div className="confidence">
      <div className="confidence-head">
        <span className="muted">{t(label)}</span>
        <span className="confidence-value">{percent(value)}</span>
      </div>
      <div
        className="confidence-track"
        role="meter"
        aria-valuenow={width}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={t('{label}: {value}', { label: t(label), value: percent(value) })}
      >
        <div className={`confidence-fill ${band}`} style={{ width: `${width}%` }} />
      </div>
      {showNote && (
        <div className="confidence-note">
          {t(NOTES[band], {
            high: Math.round(HIGH_CONFIDENCE_THRESHOLD * 100),
            medium: Math.round(MEDIUM_CONFIDENCE_THRESHOLD * 100),
          })}
        </div>
      )}
    </div>
  );
}

export default ConfidenceIndicator;
