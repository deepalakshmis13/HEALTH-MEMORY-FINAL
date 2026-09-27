import { useEffect } from 'react';
import { useT } from '../../i18n/LanguageContext';

export function Modal({ open, title, onClose, children, footer, wide = false }) {
  const t = useT();
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose?.();
      }}
    >
      <div
        className={`modal${wide ? ' wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? t(title) : t('Dialog')}
      >
        <div className="modal-header">
          <h3>{typeof title === 'string' ? t(title) : title}</h3>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label={t('Close')}
          >
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  tone = 'primary',
  onConfirm,
  onClose,
  busy,
}) {
  const t = useT();
  return (
    <Modal
      open={open}
      title={title}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button
            type="button"
            className={`btn btn-${tone}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? t('Working…') : t(confirmLabel)}
          </button>
        </>
      }
    >
      <p>{t(message)}</p>
    </Modal>
  );
}

export default Modal;
