import { useState } from 'react';
import { useT } from '../../i18n/LanguageContext';

export function ChatInput({ onSend, busy, placeholder = 'Ask a question…' }) {
  const t = useT();
  const [value, setValue] = useState('');

  const send = () => {
    const text = value.trim();
    if (!text || busy) return;
    onSend(text);
    setValue('');
  };

  return (
    <div className="chat-input-row">
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            send();
          }
        }}
        rows={1}
        placeholder={t(placeholder)}
        aria-label={t('Your question')}
        disabled={busy}
      />
      <button
        type="button"
        className="btn btn-primary"
        onClick={send}
        disabled={busy || !value.trim()}
      >
        {busy ? t('Thinking…') : t('Ask')}
      </button>
    </div>
  );
}

export default ChatInput;
