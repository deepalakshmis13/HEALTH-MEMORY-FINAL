import { Badge, PriorityBadge } from '../common/StatusBadge';
import ConfidenceIndicator from '../ingestion/ConfidenceIndicator';
import EmptyState from '../common/EmptyState';
import { formatDateTime } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

const STATUS_FILTERS = [
  { key: 'PENDING_VERIFICATION', label: 'Pending' },
  { key: 'CORRECTED', label: 'Corrected' },
  { key: 'VERIFIED', label: 'Verified' },
  { key: 'REJECTED', label: 'Rejected' },
  { key: 'ALL', label: 'All' },
];

/** The queue only ever contains low/medium-confidence clinical fields (§13). */
export function VerificationQueue({ queue = [], status, onStatus, onOpen }) {
  const t = useT();
  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('Verification Queue')}
          <span className="card-sub">
            {t(
              'Only clinically important fields read below the auto-accept threshold reach this queue',
            )}
          </span>
        </h3>
        <div className="row tight">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.key}
              type="button"
              className={`chip${status === filter.key ? ' active' : ''}`}
              onClick={() => onStatus(filter.key)}
            >
              {t(filter.label)}
            </button>
          ))}
        </div>
      </div>
      <div className="card-body flush">
        {queue.length === 0 ? (
          <EmptyState
            icon="✅"
            title={t('The queue is clear')}
            message={t(
              'Nothing is waiting for verification. High-confidence extraction goes straight into health memory with its provenance intact.',
            )}
          />
        ) : (
          <div className="stack" style={{ padding: 16 }}>
            {queue.map((item) => (
              <article
                key={item.id}
                className={`memory-card ${
                  item.priority === 'HIGH' ? 'critical' : 'attention'
                }`}
              >
                <div className="memory-card-head">
                  <h4>
                    {t(item.field_label)}: <span className="mono">{item.extracted_value}</span>
                  </h4>
                  {item.status === 'PENDING_VERIFICATION' ? (
                    <PriorityBadge priority={item.priority} />
                  ) : (
                    <Badge
                      tone={item.status === 'REJECTED' ? 'danger' : 'ok'}
                    >
                      {item.status.replace(/_/g, ' ').toLowerCase()}
                    </Badge>
                  )}
                </div>

                <div className="grid grid-2" style={{ gap: 12 }}>
                  <div className="kv-list">
                    <div className="kv">
                      <span className="kv-key">{t('Patient')}</span>
                      <span className="kv-val">
                        {item.patient_name}
                        {item.patient_age ? `, ${item.patient_age}` : ''}
                      </span>
                    </div>
                    <div className="kv">
                      <span className="kv-key">{t('Document')}</span>
                      <span className="kv-val">
                        {item.document_name || t('Typed or spoken entry')}
                        {item.is_handwritten && ' ✍️'}
                      </span>
                    </div>
                    <div className="kv">
                      <span className="kv-key">{t('OCR result')}</span>
                      <span className="kv-val mono">“{item.extracted_value}”</span>
                    </div>
                  </div>
                  <ConfidenceIndicator value={item.confidence} showNote />
                </div>

                <div className="memory-card-meta">
                  <span>{formatDateTime(item.created_at)}</span>
                  {item.result && (
                    <Badge tone="ok">
                      {t('{action} by {name}', {
                        action: item.result.action,
                        name: item.result.reviewer_name,
                      })}
                    </Badge>
                  )}
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    style={{ marginLeft: 'auto' }}
                    onClick={() => onOpen(item)}
                  >
                    {item.status === 'PENDING_VERIFICATION'
                      ? t('Review & verify')
                      : t('View')}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default VerificationQueue;
