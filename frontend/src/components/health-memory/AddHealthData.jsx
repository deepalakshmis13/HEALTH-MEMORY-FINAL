import { useState } from 'react';
import TextInput from '../ingestion/TextInput';
import VoiceInput from '../ingestion/VoiceInput';
import ScanUpload from '../ingestion/ScanUpload';
import OCRResult from '../ingestion/OCRResult';
import { Badge } from '../common/StatusBadge';
import { PageHeader } from '../common/PageHeader';
import { useToast } from '../common/Toast';
import ingestionService from '../../services/ingestionService';
import { percent, titleCase } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';

const METHODS = [
  {
    key: 'text',
    icon: '📝',
    title: 'TEXT',
    sub: 'Enter health information manually',
  },
  {
    key: 'voice',
    icon: '🎙',
    title: 'VOICE',
    sub: 'Tell us about your health',
  },
  {
    key: 'scan',
    icon: '📄',
    title: 'SCAN & UPLOAD',
    sub: 'Upload medical reports or documents',
  },
];

/** The three ingestion methods that all feed the same health-memory pipeline. */
export function AddHealthData({ patientId, onSaved, firstTime = false }) {
  const t = useT();
  const toast = useToast();
  const [method, setMethod] = useState(null);
  const [busy, setBusy] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [textResult, setTextResult] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  const reset = () => {
    setMethod(null);
    setTextResult(null);
    setUploadResult(null);
    setProgressStep(0);
  };

  const handleText = async (text, entryDate) => {
    setBusy(true);
    try {
      const result = await ingestionService.text(patientId, text, entryDate);
      setTextResult(result);
      toast.success(result.message, t('Saved to health memory'));
      onSaved?.();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setBusy(false);
    }
  };

  const handleVoice = async (transcript, extras) => {
    setBusy(true);
    try {
      const result = await ingestionService.voice(patientId, transcript, extras);
      setTextResult(result);
      toast.success(result.message, t('Voice entry saved'));
      onSaved?.();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setBusy(false);
    }
  };

  const handleUpload = async (file, isHandwritten) => {
    setBusy(true);
    setProgressStep(0);
    const ticker = window.setInterval(
      () => setProgressStep((step) => Math.min(step + 1, 4)),
      520,
    );
    try {
      const result = await ingestionService.upload(patientId, file, { isHandwritten });
      setUploadResult(result);
      toast[result.verification_tasks.length ? 'warning' : 'success'](
        result.message,
        result.verification_tasks.length
          ? t('Verification required')
          : t('Document added to health memory'),
      );
      onSaved?.();
    } catch (error) {
      toast.error(error.message, t('Unable to process document'));
    } finally {
      window.clearInterval(ticker);
      setBusy(false);
    }
  };

  if (uploadResult) {
    return (
      <OCRResult
        result={uploadResult}
        routing={uploadResult.doctor_routing}
        onDone={reset}
      />
    );
  }

  if (textResult) {
    const entities = textResult.entities || {};
    return (
      <div className="stack">
        <div className="alert alert-ok">
          <span className="alert-icon" aria-hidden="true">
            ✅
          </span>
          <div className="alert-body">
            <div className="alert-title">{t('Added to your health memory')}</div>
            {textResult.message}
          </div>
        </div>

        <section className="card">
          <div className="card-header">
            <h3>
              {t('What we recognised')}
              <span className="card-sub">
                {t('Source: {source} · confidence {value}', {
                  source: textResult.source,
                  value: percent(textResult.confidence),
                })}
              </span>
            </h3>
          </div>
          <div className="card-body">
            <div className="kv-list">
              {entities.doctor && (
                <div className="kv">
                  <span className="kv-key">{t('Doctor')}</span>
                  <span className="kv-val">
                    {entities.doctor.name}
                    {entities.doctor.specialty ? ` — ${entities.doctor.specialty}` : ''}
                    {entities.doctor.hospital ? ` (${entities.doctor.hospital})` : ''}
                  </span>
                </div>
              )}
              {(entities.medications || []).length > 0 && (
                <div className="kv">
                  <span className="kv-key">{t('Medicines')}</span>
                  <span className="kv-val">
                    {entities.medications
                      .map((medication) =>
                        [medication.name, medication.dose, medication.frequency]
                          .filter(Boolean)
                          .join(' — '),
                      )
                      .join('; ')}
                  </span>
                </div>
              )}
              {(entities.symptoms || []).length > 0 && (
                <div className="kv">
                  <span className="kv-key">{t('Symptoms')}</span>
                  <span className="kv-val">
                    {entities.symptoms.map(titleCase).join(', ')}
                  </span>
                </div>
              )}
              {(entities.diagnoses || []).length > 0 && (
                <div className="kv">
                  <span className="kv-key">{t('Conditions mentioned')}</span>
                  <span className="kv-val">
                    {entities.diagnoses.map(titleCase).join(', ')}
                  </span>
                </div>
              )}
              {entities.event_date_label && (
                <div className="kv">
                  <span className="kv-key">{t('Date')}</span>
                  <span className="kv-val">{entities.event_date_label}</span>
                </div>
              )}
            </div>

            {textResult.doctor_routing?.doctor && (
              <div className="alert alert-info mt-2">
                <span className="alert-icon" aria-hidden="true">
                  🩺
                </span>
                <div className="alert-body">
                  <div className="alert-title">
                    {textResult.doctor_routing.doctor.name}
                  </div>
                  {textResult.doctor_routing.message}
                </div>
              </div>
            )}

            {textResult.verification_tasks?.length > 0 && (
              <div className="alert alert-warn mt-2">
                <span className="alert-icon" aria-hidden="true">
                  🔍
                </span>
                <div className="alert-body">
                  {t(
                    '{count} detail(s) were sent to a reviewer to confirm before they are treated as verified.',
                    { count: textResult.verification_tasks.length },
                  )}
                </div>
              </div>
            )}
          </div>
        </section>

        <div className="row">
          <button type="button" className="btn btn-primary" onClick={reset}>
            {t('Add something else')}
          </button>
        </div>
      </div>
    );
  }

  if (!method) {
    return (
      <div className="stack">
        {firstTime && (
          <div className="alert alert-info">
            <span className="alert-icon" aria-hidden="true">
              👋
            </span>
            <div className="alert-body">
              <div className="alert-title">{t('Welcome to My Health Memory')}</div>
              {t(
                'Your health memory is empty. Add your first piece of information — you can type it, say it, or scan a document.',
              )}
            </div>
          </div>
        )}
        <PageHeader
          title={t('Add health information')}
          subtitle={t(
            'How would you like to add your health information? All three go into the same health memory, and each one keeps a record of where it came from.',
          )}
        />
        <div className="action-tiles">
          {METHODS.map((item) => (
            <button
              key={item.key}
              type="button"
              className="action-tile"
              onClick={() => setMethod(item.key)}
            >
              <span className="tile-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span className="tile-title">{t(item.title)}</span>
              <span className="tile-sub">{t(item.sub)}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const active = METHODS.find((item) => item.key === method);

  return (
    <div className="stack">
      <div className="row">
        <button type="button" className="btn btn-ghost" onClick={reset} disabled={busy}>
          ← {t('Choose a different way')}
        </button>
        <Badge tone="primary" large>
          {active.icon} {t(active.title)}
        </Badge>
      </div>

      <section className="card">
        <div className="card-header">
          <h3>
            {t(active.sub)}
            <span className="card-sub">
              {t('Everything you add keeps its source and the date it was recorded.')}
            </span>
          </h3>
        </div>
        <div className="card-body">
          {method === 'text' && <TextInput onSubmit={handleText} busy={busy} />}
          {method === 'voice' && <VoiceInput onSubmit={handleVoice} busy={busy} />}
          {method === 'scan' && (
            <ScanUpload
              onUpload={handleUpload}
              busy={busy}
              progressStep={progressStep}
            />
          )}
        </div>
      </section>
    </div>
  );
}

export default AddHealthData;
