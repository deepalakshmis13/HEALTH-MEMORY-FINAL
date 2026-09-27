import { useEffect, useState } from 'react';
import Modal from '../common/Modal';
import { Badge } from '../common/StatusBadge';
import ConfidenceIndicator from '../ingestion/ConfidenceIndicator';
import LoadingState from '../common/LoadingState';
import { useToast } from '../common/Toast';
import documentService from '../../services/documentService';
import { reviewerService } from '../../services/roleServices';
import { formatDateTime, percent } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

/**
 * The verification screen (§14): original document, OCR output, confidence,
 * extracted fields and the patient's medication context — then confirm,
 * correct, reject or add a clarification.
 */
export function OCRVerification({ taskId, open, onClose, onResolved }) {
  const t = useT();
  const toast = useToast();
  const [task, setTask] = useState(null);
  const [preview, setPreview] = useState(null);
  const [corrected, setCorrected] = useState('');
  const [clarification, setClarification] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [mode, setMode] = useState('confirm');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || !taskId) return undefined;
    setTask(null);
    setPreview(null);
    setMode('confirm');
    setRejectReason('');
    setClarification('');

    let objectUrl = null;
    reviewerService
      .task(taskId)
      .then((data) => {
        setTask(data);
        setCorrected(data.extracted_value || '');
        if (data.document_id) {
          documentService.fileUrl(data.document_id).then((result) => {
            if (result) {
              objectUrl = result.url;
              setPreview(result);
            }
          });
        }
      })
      .catch((error) => toast.error(error.message));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, taskId]);

  const act = async (action) => {
    setBusy(true);
    try {
      let result;
      if (action === 'verify') {
        result = await reviewerService.verify(taskId, clarification || null);
        toast.success(
          t(
            '{field} confirmed as “{value}”. The original OCR reading and its confidence are preserved.',
            { field: task.field_label, value: task.extracted_value },
          ),
          t('Verified'),
        );
      } else if (action === 'correct') {
        if (!corrected.trim()) {
          toast.warning(t('Enter the corrected value.'));
          setBusy(false);
          return;
        }
        result = await reviewerService.correct(taskId, corrected.trim(), clarification);
        toast.success(
          t('Corrected to “{value}” and written to verified health memory.', {
            value: corrected.trim(),
          }),
          t('Corrected and verified'),
        );
      } else {
        if (!rejectReason.trim()) {
          toast.warning(t('A reason is required to reject an extraction.'));
          setBusy(false);
          return;
        }
        result = await reviewerService.reject(taskId, rejectReason.trim());
        toast.info(
          t('Rejected. This reading will not be used by retrieval or the assistants.'),
          t('Rejected'),
        );
      }
      onResolved?.(result);
      onClose();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setBusy(false);
    }
  };

  const resolved = task && task.status !== 'PENDING_VERIFICATION';

  return (
    <Modal
      open={open}
      onClose={onClose}
      wide
      title={
        task
          ? t('Verify {field} — {name}', {
              field: task.field_label,
              name: task.patient_name,
            })
          : t('Loading verification task…')
      }
      footer={
        task && !resolved ? (
          <>
            <button
              type="button"
              className="btn btn-outline"
              onClick={onClose}
              disabled={busy}
            >
              {t('Cancel')}
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={() => (mode === 'reject' ? act('reject') : setMode('reject'))}
              disabled={busy}
            >
              {mode === 'reject' ? t('Confirm rejection') : t('Reject')}
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => (mode === 'correct' ? act('correct') : setMode('correct'))}
              disabled={busy}
            >
              {mode === 'correct' ? t('Save correction') : t('Correct')}
            </button>
            <button
              type="button"
              className="btn btn-success"
              onClick={() => act('verify')}
              disabled={busy}
            >
              {t('Verify as read')}
            </button>
          </>
        ) : (
          <button type="button" className="btn btn-outline" onClick={onClose}>
            {t('Close')}
          </button>
        )
      }
    >
      {!task && <LoadingState message={t('Loading the document and its OCR result…')} />}

      {task && (
        <div className="grid grid-2">
          <div className="stack">
            <div>
              <div className="form-label">{t('Original document')}</div>
              {preview ? (
                preview.type.startsWith('image/') ? (
                  <img
                    className="doc-image"
                    src={preview.url}
                    alt={task.document_name}
                  />
                ) : preview.type === 'application/pdf' ? (
                  <iframe
                    title={task.document_name}
                    src={preview.url}
                    style={{
                      width: '100%',
                      height: 360,
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                    }}
                  />
                ) : (
                  <div className="doc-preview">{task.ocr_raw_text}</div>
                )
              ) : (
                <p className="muted small">
                  {task.document_id
                    ? t('Loading the stored document…')
                    : t('This value came from a typed or spoken entry, not a document.')}
                </p>
              )}
            </div>

            <div>
              <div className="form-label">{t('OCR text')}</div>
              <div className="doc-preview">
                {task.ocr_raw_text || t('No OCR text for this entry.')}
              </div>
            </div>
          </div>

          <div className="stack">
            <div className="alert alert-warn">
              <span className="alert-icon" aria-hidden="true">
                🔍
              </span>
              <div className="alert-body">
                <div className="alert-title">{t('Why this needs confirmation')}</div>
                {task.reason}
              </div>
            </div>

            <div className="kv-list">
              <div className="kv">
                <span className="kv-key">{t('Field')}</span>
                <span className="kv-val">{t(task.field_label)}</span>
              </div>
              <div className="kv">
                <span className="kv-key">{t('OCR read')}</span>
                <span className="kv-val mono">“{task.extracted_value}”</span>
              </div>
              <div className="kv">
                <span className="kv-key">{t('Engine')}</span>
                <span className="kv-val">{task.ocr_engine || '—'}</span>
              </div>
              <div className="kv">
                <span className="kv-key">{t('Document')}</span>
                <span className="kv-val">
                  {task.document_name || t('Typed / spoken entry')}
                  {task.is_handwritten && ` ✍️ ${t('handwritten')}`}
                </span>
              </div>
            </div>

            <ConfidenceIndicator value={task.confidence} showNote />

            {task.ocr_fields?.length > 0 && (
              <div>
                <div className="form-label">{t('All fields from this document')}</div>
                <div className="table-wrap">
                  <table className="data" style={{ minWidth: 300 }}>
                    <tbody>
                      {task.ocr_fields.map((field, index) => (
                        <tr key={`${field.field}-${index}`}>
                          <td className="small strong">{field.label}</td>
                          <td className="small mono">{field.value}</td>
                          <td className="small nowrap">
                            {percent(field.confidence)}
                            {field.needs_verification && ' ⚑'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {task.patient_context && (
              <div>
                <div className="form-label">
                  {t('Patient medication context (consent-checked)')}
                </div>
                <div className="row tight">
                  {task.patient_context.medications.length === 0 && (
                    <span className="muted small">{t('No active medications.')}</span>
                  )}
                  {task.patient_context.medications.map((medication) => (
                    <Badge key={medication.id} tone="outline">
                      {medication.name} {medication.dose}
                    </Badge>
                  ))}
                </div>
                {task.patient_context.allergies.length > 0 && (
                  <div className="row tight mt-1">
                    {task.patient_context.allergies.map((allergy) => (
                      <Badge key={allergy.id} tone="danger">
                        ⚠️ {allergy.substance}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {resolved ? (
              <div className="alert alert-ok">
                <span className="alert-icon" aria-hidden="true">
                  ✅
                </span>
                <div className="alert-body">
                  <div className="alert-title">
                    {t('{status} by {name}', {
                      status: task.status.replace(/_/g, ' '),
                      name: task.result?.reviewer_name,
                    })}
                  </div>
                  {t('Original OCR “{value}” at {confidence} →', {
                    value: task.result?.original_value,
                    confidence: task.result?.original_confidence_percent,
                  })}{' '}
                  <strong>{task.result?.corrected_value || t('not accepted')}</strong>{' '}
                  {t('on {date}.', {
                    date: formatDateTime(task.result?.verified_at),
                  })}
                  {task.result?.clarification && (
                    <div className="small mt-1">
                      {t('Clarification:')} {task.result.clarification}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                {mode === 'correct' && (
                  <div className="field">
                    <label htmlFor="corrected">{t('Corrected value')}</label>
                    <input
                      id="corrected"
                      value={corrected}
                      onChange={(event) => setCorrected(event.target.value)}
                      autoFocus
                    />
                    <div className="hint">
                      {t(
                        'The original OCR reading and its confidence are kept — this records the correction alongside them, never instead of them.',
                      )}
                    </div>
                  </div>
                )}

                {mode === 'reject' && (
                  <div className="field">
                    <label htmlFor="reject-reason">{t('Reason for rejection')}</label>
                    <textarea
                      id="reject-reason"
                      value={rejectReason}
                      onChange={(event) => setRejectReason(event.target.value)}
                      rows={3}
                      placeholder={t(
                        'e.g. Illegible — cannot confirm the drug name. Prescriber must be contacted.',
                      )}
                      autoFocus
                    />
                  </div>
                )}

                {mode !== 'reject' && (
                  <div className="field">
                    <label htmlFor="clarification">{t('Clarification (optional)')}</label>
                    <textarea
                      id="clarification"
                      value={clarification}
                      onChange={(event) => setClarification(event.target.value)}
                      rows={2}
                      placeholder={t(
                        "e.g. Confirmed against the prescriber's letterhead.",
                      )}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}

export default OCRVerification;
