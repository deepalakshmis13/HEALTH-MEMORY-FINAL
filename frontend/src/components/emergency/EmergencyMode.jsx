import { useEffect } from 'react';
import EmergencyCard from './EmergencyCard';
import { useT } from '../../i18n/LanguageContext';

/**
 * Emergency mode strips the interface back to the information that matters in
 * an emergency, at a size that can be read at arm's length (§31).
 */
export function EmergencyMode({ card, open, onClose }) {
  const t = useT();
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open || !card) return null;

  return (
    <div className="emergency-mode senior-scale" role="dialog" aria-modal="true">
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        <div className="row between mb-2">
          <h1>{t('Emergency information')}</h1>
          <div className="row">
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => window.print()}
            >
              🖨 {t('Print')}
            </button>
            <button type="button" className="btn btn-primary" onClick={onClose}>
              {t('Close')}
            </button>
          </div>
        </div>
        <EmergencyCard card={card} />
        <p className="muted mt-2">
          {t(
            'This card shows only the information needed in an emergency. Nothing here is a diagnosis or an instruction — call the emergency contact or the primary doctor for decisions.',
          )}
        </p>
      </div>
    </div>
  );
}

export default EmergencyMode;
