import { useState } from 'react';
import { useT } from '../../i18n/LanguageContext';

const EXAMPLE =
  'I visited Dr. Kumar on 10 August because of dizziness. He asked me to ' +
  'continue my blood pressure medicine Amlodipine 5 mg once daily.';

export function TextInput({ onSubmit, busy }) {
  const t = useT();
  const [text, setText] = useState('');
  const [entryDate, setEntryDate] = useState('');

  const submit = (event) => {
    event.preventDefault();
    if (text.trim().length < 4) return;
    onSubmit(text.trim(), entryDate || null);
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label htmlFor="health-text">
          {t('Tell us what happened, in your own words')}
        </label>
        <textarea
          id="health-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t(EXAMPLE)}
          rows={6}
          disabled={busy}
        />
        <div className="hint">
          {t(
            'Mention the doctor, the date, your medicines and how you felt. We will pick out the details and keep the original wording.',
          )}
        </div>
      </div>

      <div className="field">
        <label htmlFor="entry-date">{t('Date this happened (optional)')}</label>
        <input
          id="entry-date"
          type="date"
          value={entryDate}
          onChange={(event) => setEntryDate(event.target.value)}
          disabled={busy}
          style={{ maxWidth: 240 }}
        />
      </div>

      <div className="alert alert-neutral mb-2">
        <span className="alert-icon" aria-hidden="true">
          🔖
        </span>
        <div className="alert-body">
          {t('This will be saved as')} <strong>{t('Patient/Guardian entered')}</strong>.{' '}
          {t('It is kept separate from information confirmed by a doctor.')}
        </div>
      </div>

      <div className="row">
        <button
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={busy || text.trim().length < 4}
        >
          {busy ? t('Saving to health memory…') : t('Save to my health memory')}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setText(EXAMPLE)}
          disabled={busy}
        >
          {t('Use the example')}
        </button>
      </div>
    </form>
  );
}

export default TextInput;
