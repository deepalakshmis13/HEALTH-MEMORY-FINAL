import { useState } from 'react';
import { Badge } from '../common/StatusBadge';
import { PipelineProgress } from '../common/LoadingState';
import EvidencePanel from '../chatbot/EvidencePanel';
import { useToast } from '../common/Toast';
import { doctorService } from '../../services/roleServices';
import { LOADING_MESSAGES } from '../../utils/constants';
import { formatDateTime } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

const STEPS = [
  LOADING_MESSAGES.consent,
  LOADING_MESSAGES.retrieval,
  LOADING_MESSAGES.clinical,
  LOADING_MESSAGES.summary,
];

/** One-click visit summary — generated, reviewed, edited, then saved (§29). */
export function VisitSummary({ patientId, patientName }) {
  const t = useT();
  const toast = useToast();
  const [summary, setSummary] = useState(null);
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [saved, setSaved] = useState(false);

  const generate = async () => {
    setBusy(true);
    setSaved(false);
    setStep(0);
    const ticker = window.setInterval(
      () => setStep((value) => Math.min(value + 1, STEPS.length - 1)),
      620,
    );
    try {
      const result = await doctorService.visitSummary(patientId);
      setSummary(result);
      setContent(result.content);
    } catch (error) {
      toast.error(error.message, t('Unable to generate summary'));
    } finally {
      window.clearInterval(ticker);
      setBusy(false);
    }
  };

  const save = async () => {
    if (!summary) return;
    setBusy(true);
    try {
      await doctorService.saveVisitSummary(summary.summary_id, content);
      setSaved(true);
      toast.success(
        t('Saved to the patient’s health memory as a doctor-recorded entry.'),
        t('Visit summary saved'),
      );
    } catch (error) {
      toast.error(error.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card">
      <div className="card-header">
        <h3>
          {t('One-click Visit Summary')}
          <span className="card-sub">
            {t(
              'Assembled from consented health memory · never becomes the medical record until you save it',
            )}
          </span>
        </h3>
        <button
          type="button"
          className="btn btn-primary"
          onClick={generate}
          disabled={busy || !patientId}
        >
          {summary ? t('Regenerate') : t('Generate Visit Summary')}
        </button>
      </div>

      <div className="card-body">
        {busy && !summary && (
          <PipelineProgress
            steps={STEPS.map((message) => t(message))}
            activeIndex={step}
          />
        )}

        {!busy && !summary && (
          <p className="muted">
            {t(
              'Generate a longitudinal summary for {name}: overview, recent history, current medications, medication changes, lab results, hospital visits, patient-reported information, caregiver observations, alerts, unresolved issues and suggested questions.',
              { name: patientName || t('this patient') },
            )}
          </p>
        )}

        {summary && (
          <div className="stack">
            <div className="alert alert-warn">
              <span className="alert-icon" aria-hidden="true">
                ✨
              </span>
              <div className="alert-body">
                <div className="alert-title">{t('AI-generated draft')}</div>
                {summary.disclaimer}
              </div>
            </div>

            <div className="row">
              <Badge tone={saved ? 'ok' : 'outline'}>
                {saved ? t('Saved to health memory') : t('Draft — not saved')}
              </Badge>
              <Badge tone="outline">{summary.provider}</Badge>
              <Badge tone="outline">
                {t('{n} sources', { n: summary.sources.length })}
              </Badge>
              <span className="tiny faint">
                {t('Generated {time}', {
                  time: formatDateTime(summary.generated_at),
                })}
              </span>
            </div>

            <div className="field">
              <label htmlFor="summary-content">
                {t('Review and edit before saving')}
              </label>
              <textarea
                id="summary-content"
                className="summary-output"
                value={content}
                onChange={(event) => {
                  setContent(event.target.value);
                  setSaved(false);
                }}
                rows={22}
              />
            </div>

            <EvidencePanel
              sources={summary.sources}
              explanation={summary.explanation}
            />

            <div className="row">
              <button
                type="button"
                className="btn btn-success"
                onClick={save}
                disabled={busy || saved}
              >
                {saved ? t('Saved') : t('Save to health memory')}
              </button>
              <button
                type="button"
                className="btn btn-outline"
                onClick={generate}
                disabled={busy}
              >
                {t('Regenerate')}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => navigator.clipboard?.writeText(content)}
              >
                {t('Copy')}
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

export default VisitSummary;
