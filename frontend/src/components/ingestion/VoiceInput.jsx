import { useEffect, useRef, useState } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';

const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

/**
 * Speech options. The Web Speech API accepts one recognition locale at a
 * time, so mixed Tamil-English speech is recognised with the Tamil recogniser,
 * which keeps embedded English words rather than discarding them. Whatever
 * comes back is stored as the patient's own words and read — never diagnosed —
 * on the server.
 */
const SPEECH_MODES = [
  { key: 'en', label: 'English', locale: 'en-IN' },
  { key: 'ta', label: 'தமிழ்', locale: 'ta-IN' },
  { key: 'mixed', label: 'தமிழ் + English', locale: 'ta-IN' },
];

/**
 * Browser speech recognition where available, with a typed transcript
 * fallback everywhere else — the pipeline is identical either way.
 */
export function VoiceInput({ onSubmit, busy }) {
  const { t, language, speechLocale } = useLanguage();
  const [speechMode, setSpeechMode] = useState(() => (language === 'ta' ? 'mixed' : 'en'));
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interim, setInterim] = useState('');
  const [confidence, setConfidence] = useState(0.9);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState('');
  const recognitionRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => () => {
    recognitionRef.current?.stop?.();
    if (timerRef.current) window.clearInterval(timerRef.current);
  }, []);

  const start = () => {
    setError('');
    if (!SpeechRecognition) {
      setError(
        t(
          'Your browser cannot record speech. Please type what you want to say below — ' +
            'it will be saved exactly the same way.',
        ),
      );
      return;
    }
    const recognition = new SpeechRecognition();
    const mode = SPEECH_MODES.find((item) => item.key === speechMode);
    recognition.lang = mode?.locale || speechLocale || 'en-IN';
    recognition.continuous = true;
    recognition.interimResults = true;
    // Mixed speech switches script mid-sentence, so keep the alternatives the
    // recogniser offers rather than only its single best guess.
    recognition.maxAlternatives = speechMode === 'mixed' ? 3 : 1;

    recognition.onresult = (event) => {
      let finalText = '';
      let pending = '';
      let best = 0;
      let count = 0;
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) {
          finalText += result[0].transcript;
          best += result[0].confidence || 0.9;
          count += 1;
        } else {
          pending += result[0].transcript;
        }
      }
      if (finalText) {
        setTranscript((current) => `${current}${current ? ' ' : ''}${finalText.trim()}`);
        if (count) setConfidence(Math.min(0.97, Math.max(0.45, best / count)));
      }
      setInterim(pending);
    };

    recognition.onerror = (event) => {
      setError(
        event.error === 'not-allowed'
          ? t('Microphone permission was refused. You can type your entry instead.')
          : t(
              'Speech recognition stopped unexpectedly. You can type your entry instead.',
            ),
      );
      stop();
    };

    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
    setSeconds(0);
    timerRef.current = window.setInterval(
      () => setSeconds((value) => value + 1),
      1000,
    );
  };

  const stop = () => {
    recognitionRef.current?.stop?.();
    recognitionRef.current = null;
    setListening(false);
    setInterim('');
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const submit = () => {
    const text = `${transcript} ${interim}`.trim();
    if (text.length < 4) return;
    onSubmit(text, {
      durationSeconds: seconds || null,
      recognitionConfidence: SpeechRecognition ? confidence : 0.82,
    });
  };

  return (
    <div>
      <div className="card" style={{ background: 'var(--surface-soft)' }}>
        <div className="card-body center">
          <div className="field" style={{ maxWidth: 320, margin: '0 auto 14px' }}>
            <label htmlFor="voice-language">{t('Speaking language')}</label>
            <select
              id="voice-language"
              value={speechMode}
              onChange={(event) => setSpeechMode(event.target.value)}
              disabled={listening || busy}
            >
              {SPEECH_MODES.map((mode) => (
                <option key={mode.key} value={mode.key}>
                  {mode.label}
                </option>
              ))}
            </select>
            <div className="hint">
              {t('You can speak in English, in Tamil, or mix both in one sentence.')}
            </div>
          </div>
          <button
            type="button"
            className={`btn btn-lg ${listening ? 'btn-danger' : 'btn-primary'}`}
            onClick={listening ? stop : start}
            disabled={busy}
            style={{ minWidth: 260 }}
          >
            {listening
              ? t('⏹ Stop recording ({seconds}s)', { seconds })
              : t('🎙 Record health information')}
          </button>
          <p className="muted mt-2 mb-1">
            {listening
              ? t('Listening… speak clearly and naturally.')
              : speechMode === 'en'
                ? t(
                    'Tell us about your health — for example: “I met Dr Kumar last Monday and he changed my blood pressure medicine.”',
                  )
                : t(
                    'Tell us about your health — for example: “எனக்கு இரண்டு நாளாக தலை வலிக்குது.”',
                  )}
          </p>
          {!SpeechRecognition && (
            <p className="tiny faint">
              {t(
                'Speech recognition is not available in this browser — type your entry below instead.',
              )}
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="alert alert-warn mt-2">
          <span className="alert-icon" aria-hidden="true">
            ⚠️
          </span>
          <div className="alert-body">{error}</div>
        </div>
      )}

      <div className="field mt-2">
        <label htmlFor="voice-transcript">{t('Transcript')}</label>
        <textarea
          id="voice-transcript"
          value={`${transcript}${interim ? ` ${interim}` : ''}`}
          onChange={(event) => {
            setTranscript(event.target.value);
            setInterim('');
          }}
          rows={5}
          placeholder={t(
            'Your words will appear here. You can correct them before saving.',
          )}
          disabled={busy}
        />
        <div className="hint">
          {t(
            'You can edit the transcript before saving. The original wording is kept in your health memory.',
          )}
        </div>
      </div>

      <div className="alert alert-neutral mb-2">
        <span className="alert-icon" aria-hidden="true">
          🔖
        </span>
        <div className="alert-body">
          {t('Saved as')} <strong>{t('Patient Reported')}</strong>.{' '}
          {t('What you say is never turned into a confirmed diagnosis.')}{' '}
          {speechMode !== 'en' &&
            t(
              'Your Tamil words are stored exactly as you said them, with a plain English reading added for your doctor.',
            )}
        </div>
      </div>

      <div className="row">
        <button
          type="button"
          className="btn btn-primary btn-lg"
          onClick={submit}
          disabled={busy || `${transcript}${interim}`.trim().length < 4}
        >
          {busy ? t('Saving to health memory…') : t('Save voice entry')}
        </button>
        {transcript && !busy && (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setTranscript('');
              setInterim('');
            }}
          >
            {t('Clear')}
          </button>
        )}
      </div>
    </div>
  );
}

export default VoiceInput;
