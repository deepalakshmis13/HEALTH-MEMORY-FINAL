import { useT } from '../../i18n/LanguageContext';

export function LoadingState({ message = 'Loading…', inline = false }) {
  const t = useT();
  if (inline) {
    return (
      <span className="row tight muted small">
        <span className="spinner sm" aria-hidden="true" />
        {t(message)}
      </span>
    );
  }
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{t(message)}</span>
    </div>
  );
}

export function SkeletonRows({ rows = 3 }) {
  return (
    <div className="stack" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="skeleton"
          style={{ width: `${100 - index * 12}%` }}
        />
      ))}
    </div>
  );
}

/** Named pipeline progress — "Recognising handwriting…" etc. (§49) */
export function PipelineProgress({ steps, activeIndex }) {
  const t = useT();
  return (
    <div className="pipeline-steps">
      {steps.map((step, index) => {
        const state =
          index < activeIndex ? 'done' : index === activeIndex ? 'active' : '';
        return (
          <div key={step} className={`pipeline-step ${state}`}>
            <span className="ps-dot" aria-hidden="true">
              {index < activeIndex ? '✓' : ''}
            </span>
            <span>{t(step)}</span>
            {index === activeIndex && <span className="spinner sm" aria-hidden="true" />}
          </div>
        );
      })}
    </div>
  );
}

export default LoadingState;
