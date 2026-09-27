import ConfidenceIndicator from './ConfidenceIndicator';
import { Badge, PriorityBadge } from '../common/StatusBadge';
import { percent, truncate } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

/** The OCR read-out shown right after a document is processed (§10, §11). */
export function OCRResult({ result, routing, onDone, onViewQueue }) {
  const t = useT();
  if (!result) return null;
  const { ocr } = result;
  const flagged = (ocr.fields || []).filter((field) => field.needs_verification);
  const accepted = (ocr.fields || []).filter((field) => !field.needs_verification);

  return (
    <div className="stack">
      <div className="card">
        <div className="card-header">
          <h3>
            {ocr.document_type_label}
            <span className="card-sub">
              {result.document.filename} · {t('engine {name}', { name: ocr.engine })}
            </span>
          </h3>
          <Badge tone={ocr.handwriting_detected ? 'warn' : 'info'}>
            {ocr.handwriting_detected
              ? t('✍️ Handwriting recognition')
              : t('📄 Printed text')}
          </Badge>
        </div>
        <div className="card-body">
          <div className="grid grid-2">
            <div className="kv-list">
              <div className="kv">
                <span className="kv-key">{t('OCR status')}</span>
                <span className="kv-val">{t('Processed')}</span>
              </div>
              <div className="kv">
                <span className="kv-key">{t('Detection basis')}</span>
                <span className="kv-val">{ocr.handwriting_reason}</span>
              </div>
              <div className="kv">
                <span className="kv-key">{t('Recognition confidence')}</span>
                <span className="kv-val">{percent(ocr.recognition_confidence)}</span>
              </div>
              <div className="kv">
                <span className="kv-key">{t('Fields extracted')}</span>
                <span className="kv-val">{(ocr.fields || []).length}</span>
              </div>
            </div>
            <ConfidenceIndicator
              value={ocr.overall_confidence}
              label="Document confidence"
              showNote
            />
          </div>

          <div
            className={`alert mt-2 ${flagged.length ? 'alert-warn' : 'alert-ok'}`}
          >
            <span className="alert-icon" aria-hidden="true">
              {flagged.length ? '🔍' : '✅'}
            </span>
            <div className="alert-body">
              <div className="alert-title">
                {flagged.length
                  ? t('{count} field(s) sent for reviewer verification', {
                      count: flagged.length,
                    })
                  : t('Accepted into health memory')}
              </div>
              {result.message}
            </div>
          </div>
        </div>
      </div>

      {flagged.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>
              {t('Needs human confirmation')}
              <span className="card-sub">
                {t('Clinically important fields read below the auto-accept threshold')}
              </span>
            </h3>
          </div>
          <div className="card-body flush">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>{t('Field')}</th>
                    <th>{t('OCR read')}</th>
                    <th style={{ width: 170 }}>{t('Confidence')}</th>
                    <th>{t('Routing')}</th>
                  </tr>
                </thead>
                <tbody>
                  {flagged.map((field, index) => (
                    <tr key={`${field.field}-${index}`}>
                      <td className="strong">{field.label}</td>
                      <td>
                        <span className="mono">{field.value || '—'}</span>
                        {field.ocr_reading && field.ocr_reading !== field.value && (
                          <div className="tiny faint">
                            {t('raw')}: “{field.ocr_reading}”
                          </div>
                        )}
                      </td>
                      <td>
                        <ConfidenceIndicator value={field.confidence} label="" />
                      </td>
                      <td>
                        <PriorityBadge priority={field.priority} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {accepted.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>
              {t('Accepted into health memory')}
              <span className="card-sub">
                {t('Provenance preserved for every entry')}
              </span>
            </h3>
          </div>
          <div className="card-body">
            <div className="row">
              {accepted.map((field, index) => (
                <Badge key={`${field.field}-${index}`} tone="outline">
                  {field.label}: {truncate(field.value, 40)} ·{' '}
                  {percent(field.confidence)}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      )}

      {routing && (
        <div className="card">
          <div className="card-header">
            <h3>
              {t('Doctor routing')}
              <span className="card-sub">
                {t('Identified from the content of the medical record')}
              </span>
            </h3>
          </div>
          <div className="card-body">
            {routing.doctor ? (
              <div className="kv-list">
                <div className="kv">
                  <span className="kv-key">{t('Doctor')}</span>
                  <span className="kv-val">{routing.doctor.name}</span>
                </div>
                {routing.doctor.specialty && (
                  <div className="kv">
                    <span className="kv-key">{t('Specialty')}</span>
                    <span className="kv-val">{routing.doctor.specialty}</span>
                  </div>
                )}
                {routing.doctor.hospital && (
                  <div className="kv">
                    <span className="kv-key">{t('Hospital / Clinic')}</span>
                    <span className="kv-val">{routing.doctor.hospital}</span>
                  </div>
                )}
                <div className="kv">
                  <span className="kv-key">{t('Status')}</span>
                  <span className="kv-val">
                    <Badge tone={routing.routed ? 'ok' : 'outline'}>
                      {routing.routed
                        ? t('Routed to doctor')
                        : t('External / Not registered')}
                    </Badge>
                  </span>
                </div>
                <div className="kv">
                  <span className="kv-key">{t('Consent')}</span>
                  <span className="kv-val">
                    {routing.consent_granted ? t('Granted') : t('Not granted')}
                  </span>
                </div>
              </div>
            ) : (
              <p className="muted">{routing.reason || routing.message}</p>
            )}
            <p className="tiny faint mt-1">
              {t(
                'A doctor account is never created automatically. Unregistered doctors are recorded as external providers so the source is not lost.',
              )}
            </p>
          </div>
        </div>
      )}

      <div className="row">
        <button type="button" className="btn btn-primary" onClick={onDone}>
          {t('Back to my health memory')}
        </button>
        {flagged.length > 0 && onViewQueue && (
          <button type="button" className="btn btn-outline" onClick={onViewQueue}>
            {t('What happens next?')}
          </button>
        )}
      </div>

      <details className="card">
        <summary
          style={{ padding: '13px 18px', cursor: 'pointer', fontWeight: 600 }}
        >
          {t('View the raw text the recogniser produced')}
        </summary>
        <div className="card-body">
          <div className="doc-preview">{ocr.raw_text || t('(no text recognised)')}</div>
        </div>
      </details>
    </div>
  );
}

export default OCRResult;
