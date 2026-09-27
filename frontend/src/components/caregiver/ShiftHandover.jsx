import { useState } from 'react';
import { Badge } from '../common/StatusBadge';
import { PipelineProgress } from '../common/LoadingState';
import EvidencePanel from '../chatbot/EvidencePanel';
import { useToast } from '../common/Toast';
import { caregiverService } from '../../services/roleServices';
import { LOADING_MESSAGES } from '../../utils/constants';
import { formatDateTime } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

const STEPS = [
  LOADING_MESSAGES.consent,
  LOADING_MESSAGES.retrieval,
  'Collecting this shift’s medication and observations…',
  LOADING_MESSAGES.handover,
];

/** AI shift handover — reviewed by the caregiver before it is saved (§26). */
export function ShiftHandover({ shift, patientIds = [], onSaved }) {
  const t = useT();
  const toast = useToast();
  const [handover, setHandover] = useState(null);
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [saved, setSaved] = useState(false);

  const generate = async () => {
    if (!shift) return;
    setBusy(true);
    setSaved(false);
    setStep(0);
    const ticker = window.setInterval(
      () => setStep((value) => Math.min(value + 1, STEPS.length - 1)),
      600,
    );
    try {
      const result = await caregiverService.generateHandover(shift.id, patientIds);
      setHandover(result);
      setContent(result.content);
    } catch (error) {
      toast.error(error.message, t('Unable to generate handover'));
    } finally {
      window.clearInterval(ticker);
      setBusy(false);
    }
  };

  const save = async () => {
    if (!handover) return;
    setBusy(true);
    try {
      await caregiverService.saveHandover(handover.handover_id, content);
      setSaved(true);
      toast.success(
        t('Saved to each resident’s health memory for the next shift.'),
        t('Handover saved'),
      );
      onSaved?.();
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
          {t('Shift Handover AI')}
          <span className="card-sub">
            {t("Built from this shift's authorized records — review before saving")}
          </span>
        </h3>
        <button
          type="button"
          className="btn btn-primary"
          onClick={generate}
          disabled={busy || !shift}
        >
          {handover ? t('Regenerate') : t('Generate Shift Handover')}
        </button>
      </div>

      <div className="card-body">
        {busy && !handover && <PipelineProgress steps={STEPS} activeIndex={step} />}

        {!busy && !handover && (
          <p className="muted">
            {t(
              'The handover covers patient status, medication administered, missed or delayed doses, new observations, important changes, pending tasks, alerts and instructions for the next shift.',
            )}
          </p>
        )}

        {handover && (
          <div className="stack">
            <div className="alert alert-warn">
              <span className="alert-icon" aria-hidden="true">
                ✨
              </span>
              <div className="alert-body">
                <div className="alert-title">{t('AI-generated draft')}</div>
                {handover.disclaimer}
              </div>
            </div>

            <div className="row">
              <Badge tone={saved ? 'ok' : 'outline'}>
                {saved ? t('Saved to health memory') : t('Draft — not saved')}
              </Badge>
              <Badge tone="outline">{handover.provider}</Badge>
              <span className="tiny faint">
                {t('Generated {time}', {
                  time: formatDateTime(handover.generated_at),
                })}
              </span>
            </div>

            <div className="field">
              <label htmlFor="handover-content">{t('Review and edit')}</label>
              <textarea
                id="handover-content"
                className="summary-output"
                value={content}
                onChange={(event) => {
                  setContent(event.target.value);
                  setSaved(false);
                }}
                rows={20}
              />
            </div>

            <EvidencePanel sources={handover.sources} />

            <div className="row">
              <button
                type="button"
                className="btn btn-success"
                onClick={save}
                disabled={busy || saved}
              >
                {saved ? t('Saved') : t('Save handover')}
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
                onClick={() => window.print()}
              >
                🖨 {t('Print')}
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

export default ShiftHandover;
