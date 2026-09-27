import { useCallback, useEffect, useState } from 'react';
import { Badge, VerificationBadge } from '../common/StatusBadge';
import ConfidenceIndicator from '../ingestion/ConfidenceIndicator';
import EmptyState, { ErrorState } from '../common/EmptyState';
import LoadingState from '../common/LoadingState';
import Modal from '../common/Modal';
import documentService from '../../services/documentService';
import { formatDate, percent } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

/** Documents list + source viewer, shared by the patient and doctor dashboards. */
export function DocumentUpload({ patientId, refreshKey = 0, onAddDocument }) {
  const t = useT();
  const [documents, setDocuments] = useState([]);
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  const load = useCallback(() => {
    if (!patientId) return;
    setState('loading');
    documentService
      .list(patientId)
      .then((data) => {
        setDocuments(data.documents || []);
        setState('ready');
      })
      .catch((err) => {
        setError(err.message);
        setState('error');
      });
  }, [patientId]);

  useEffect(load, [load, refreshKey]);

  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Documents')}
          <span className="card-sub">
            {t('Every uploaded, scanned and handwritten source, with its OCR result')}
          </span>
        </h3>
        {onAddDocument && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onAddDocument}>
            {t('Upload a document')}
          </button>
        )}
      </div>
      <div className="card-body flush">
        {state === 'loading' && <LoadingState message={t('Loading documents…')} />}
        {state === 'error' && <ErrorState message={error} onRetry={load} />}
        {state === 'ready' && documents.length === 0 && (
          <EmptyState
            icon="📄"
            title={t('No documents yet')}
            message={t(
              'Scanned prescriptions, lab reports and handwritten doctor notes appear here once uploaded.',
            )}
          />
        )}
        {state === 'ready' && documents.length > 0 && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t('Document')}</th>
                  <th>{t('Type')}</th>
                  <th>{t('Uploaded')}</th>
                  <th style={{ width: 165 }}>{t('OCR confidence')}</th>
                  <th>{t('Verification')}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.document_id}>
                    <td>
                      <div className="strong">{document.filename}</div>
                      <div className="tiny faint">
                        {document.is_handwritten
                          ? `✍️ ${t('Handwritten')}`
                          : `📄 ${t('Printed')}`}{' '}
                        · {document.ocr_engine || t('not processed')}
                        {document.doctor ? ` · ${document.doctor}` : ''}
                      </div>
                    </td>
                    <td>
                      <Badge tone="outline">
                        {(document.document_type || 'OTHER').replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="muted small nowrap">
                      {formatDate(document.upload_date)}
                    </td>
                    <td>
                      <ConfidenceIndicator value={document.confidence} label="" />
                    </td>
                    <td>
                      <VerificationBadge
                        status={document.verification_status}
                        confidence={document.confidence}
                      />
                    </td>
                    <td className="right">
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        onClick={() => setSelected(document)}
                      >
                        {t('View')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <DocumentViewer
        document={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
      />
    </section>
  );
}

export function DocumentViewer({ document: doc, open, onClose }) {
  const t = useT();
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    let revoked = null;
    if (open && doc?.document_id && doc.has_file) {
      documentService.fileUrl(doc.document_id).then((result) => {
        if (result) {
          revoked = result.url;
          setPreview(result);
        }
      });
    }
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
      setPreview(null);
    };
  }, [open, doc]);

  if (!doc) return null;
  const ocr = doc.ocr;

  return (
    <Modal open={open} onClose={onClose} title={doc.filename} wide>
      <div className="grid grid-2">
        <div className="stack">
          <div>
            <div className="form-label">{t('Original document')}</div>
            {preview ? (
              preview.type.startsWith('image/') ? (
                <img className="doc-image" src={preview.url} alt={doc.filename} />
              ) : preview.type === 'application/pdf' ? (
                <iframe
                  title={doc.filename}
                  src={preview.url}
                  style={{
                    width: '100%',
                    height: 420,
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                  }}
                />
              ) : (
                <p className="muted small">
                  {t(
                    'Preview is not available for this file type — download it from the record instead.',
                  )}
                </p>
              )
            ) : (
              <p className="muted small">
                {doc.has_file
                  ? t('Loading the stored file…')
                  : t('The stored file is not available.')}
              </p>
            )}
          </div>
          <div className="kv-list">
            <div className="kv">
              <span className="kv-key">{t('Document type')}</span>
              <span className="kv-val">
                {(doc.document_type || 'OTHER').replace(/_/g, ' ')}
              </span>
            </div>
            <div className="kv">
              <span className="kv-key">{t('Source')}</span>
              <span className="kv-val">{doc.source?.replace(/_/g, ' ')}</span>
            </div>
            <div className="kv">
              <span className="kv-key">{t('Uploaded')}</span>
              <span className="kv-val">{formatDate(doc.upload_date)}</span>
            </div>
            <div className="kv">
              <span className="kv-key">{t('Doctor')}</span>
              <span className="kv-val">{doc.doctor || t('not identified')}</span>
            </div>
          </div>
        </div>

        <div className="stack">
          <ConfidenceIndicator
            value={doc.confidence}
            label={t('Document confidence')}
            showNote
          />
          {ocr ? (
            <>
              <div>
                <div className="form-label">{t('Extracted fields')}</div>
                <div className="table-wrap">
                  <table className="data" style={{ minWidth: 320 }}>
                    <thead>
                      <tr>
                        <th>{t('Field')}</th>
                        <th>{t('Value')}</th>
                        <th>{t('Conf.')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(ocr.fields || []).map((field, index) => (
                        <tr key={`${field.field}-${index}`}>
                          <td className="small strong">{t(field.label)}</td>
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
              <div>
                <div className="form-label">{t('OCR text')}</div>
                <div className="doc-preview">{ocr.raw_text}</div>
              </div>
            </>
          ) : (
            <p className="muted small">{t('This document has not been processed yet.')}</p>
          )}
        </div>
      </div>
    </Modal>
  );
}

export default DocumentUpload;
