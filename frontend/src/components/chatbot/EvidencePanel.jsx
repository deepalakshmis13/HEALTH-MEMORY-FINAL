import { useState } from 'react';
import { SOURCE_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

/** "Why am I seeing this?" — every AI answer shows its sources (§36). */
export function EvidencePanel({ sources = [], explanation, retrieval }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  if (!sources.length && !explanation) return null;

  return (
    <div className="evidence-panel">
      <button
        type="button"
        className="evidence-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span aria-hidden="true">{open ? '▾' : '▸'}</span>
        {sources.length === 1
          ? t('Why am I seeing this? ({count} source)', { count: sources.length })
          : t('Why am I seeing this? ({count} sources)', { count: sources.length })}
      </button>
      {open && (
        <div className="evidence-list">
          {explanation && <p className="tiny muted">{explanation}</p>}
          {sources.map((source, index) => (
            <div className="evidence-item" key={`${source.source_id}-${index}`}>
              <div className="ev-title">{source.title}</div>
              <div className="ev-meta">
                {t(SOURCE_LABELS[source.source_type] || source.source_type)} ·{' '}
                {formatDate(source.date)}
                {source.trust_level ? ` · ${t(source.trust_level)}` : ''}
                {source.verification_status === 'PENDING_VERIFICATION'
                  ? ` · ${t('not yet verified')}`
                  : ''}
              </div>
              {source.excerpt && <div className="ev-excerpt">{source.excerpt}</div>}
            </div>
          ))}
          {retrieval && (
            <div className="tiny faint">
              {t(
                'Retrieved {used} of {considered} candidate chunks after patient isolation, role authorization and consent filtering.',
                { used: retrieval.chunks_used, considered: retrieval.chunks_considered },
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default EvidencePanel;
