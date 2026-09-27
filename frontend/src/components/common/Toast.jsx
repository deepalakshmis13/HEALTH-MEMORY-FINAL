import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { useT } from '../../i18n/LanguageContext';

const ToastContext = createContext({ push: () => {} });

const ICONS = {
  success: '✅',
  error: '⚠️',
  warning: '⚠️',
  info: 'ℹ️',
};

let counter = 0;

export function ToastProvider({ children }) {
  const t = useT();
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (message, { title, tone = 'info', duration = 5000 } = {}) => {
      counter += 1;
      const id = counter;
      setToasts((current) => [...current, { id, message, title, tone }]);
      if (duration) window.setTimeout(() => dismiss(id), duration);
      return id;
    },
    [dismiss],
  );

  const value = useMemo(
    () => ({
      push,
      success: (message, title = 'Done') => push(message, { title, tone: 'success' }),
      error: (message, title = 'Something went wrong') =>
        push(message, { title, tone: 'error', duration: 7000 }),
      warning: (message, title = 'Please check') =>
        push(message, { title, tone: 'warning' }),
      info: (message, title) => push(message, { title, tone: 'info' }),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.tone}`}>
            <span aria-hidden="true">{ICONS[toast.tone] || ICONS.info}</span>
            <div style={{ flex: 1 }}>
              {toast.title && <div className="toast-title">{t(toast.title)}</div>}
              <div className="toast-msg">{t(toast.message)}</div>
            </div>
            <button
              type="button"
              className="modal-close"
              aria-label={t('Dismiss notification')}
              onClick={() => dismiss(toast.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

export default ToastProvider;
