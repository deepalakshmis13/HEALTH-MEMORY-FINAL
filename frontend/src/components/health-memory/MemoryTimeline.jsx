import { useEffect, useMemo, useState } from 'react';
import MemoryCard from './MemoryCard';
import MemoryFilters from './MemoryFilters';
import EmptyState, { ErrorState } from '../common/EmptyState';
import LoadingState from '../common/LoadingState';
import memoryService from '../../services/memoryService';
import { formatDate } from '../../utils/formatters';
import { LOADING_MESSAGES } from '../../utils/constants';
import { useT } from '../../i18n/LanguageContext';

export function MemoryTimeline({
  patientId,
  title = 'Health Memory Timeline',
  subtitle,
  compact = false,
  refreshKey = 0,
  onOpenDocument,
  emptyAction,
}) {
  const t = useT();
  const [filters, setFilters] = useState({
    search: '',
    days: '',
    source_types: '',
    event_types: '',
  });
  const [events, setEvents] = useState([]);
  const [state, setState] = useState('loading');
  const [error, setError] = useState('');
  const [indexInfo, setIndexInfo] = useState(null);

  useEffect(() => {
    if (!patientId) return undefined;
    let cancelled = false;
    setState('loading');
    memoryService
      .memory(patientId, filters)
      .then((data) => {
        if (cancelled) return;
        setEvents(data.events || []);
        setIndexInfo(data.index || null);
        setState('ready');
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setState('error');
      });
    return () => {
      cancelled = true;
    };
  }, [patientId, filters, refreshKey]);

  const grouped = useMemo(() => {
    const groups = new Map();
    events.forEach((event) => {
      const key = (event.event_date || '').slice(0, 10);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(event);
    });
    return Array.from(groups.entries()).sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }, [events]);

  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t(title)}
          <span className="card-sub">
            {t(subtitle) ||
              (indexInfo
                ? t('{count} entries · {chunks} indexed chunks in the RAG store', {
                    count: events.length,
                    chunks: indexInfo.chunks,
                  })
                : t('{count} entries', { count: events.length }))}
          </span>
        </h3>
      </div>
      <div className="card-body">
        <MemoryFilters value={filters} onChange={setFilters} />
        <div className="divider" />

        {state === 'loading' && <LoadingState message={t(LOADING_MESSAGES.clinical)} />}
        {state === 'error' && <ErrorState message={error} />}

        {state === 'ready' && grouped.length === 0 && (
          <EmptyState
            icon="🗓"
            title={t('No health memory available')}
            message={t(
              'Nothing matches these filters yet. Health information added by text, voice or scanned documents appears here with its source.',
            )}
            action={emptyAction}
          />
        )}

        {state === 'ready' && grouped.length > 0 && (
          <div className="timeline">
            {grouped.map(([date, items]) => (
              <div className="timeline-day" key={date}>
                <div className="timeline-date">{formatDate(date)}</div>
                {items.map((event) => (
                  <MemoryCard
                    key={event.id}
                    event={event}
                    compact={compact}
                    onOpenDocument={onOpenDocument}
                  />
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default MemoryTimeline;
