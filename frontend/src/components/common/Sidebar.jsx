import { ROLES } from '../../utils/constants';
import { useT } from '../../i18n/LanguageContext';

export function Sidebar({ open, onClose, user, meta, sections, active, onSelect }) {
  const t = useT();
  return (
    <>
      {open && <div className="sidebar-scrim" onClick={onClose} aria-hidden="true" />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="sidebar-brand">
          <span className="brand-mark" aria-hidden="true">
            ⊕
          </span>
          <span className="brand-text">
            <strong>{t('Health Memory')}</strong>
            <span>{t('Elder care platform')}</span>
          </span>
        </div>

        <div className="sidebar-role">
          <div className="role-label">
            {ROLES[user?.role]?.icon} {t(ROLES[user?.role]?.label || user?.role)}
          </div>
          <div className="role-name">{user?.full_name}</div>
          {meta && <div className="role-meta">{meta}</div>}
        </div>

        <nav className="sidebar-nav" aria-label={t('Dashboard sections')}>
          {sections.map((section) => (
            <div key={section.title || 'main'}>
              {section.title && (
                <div className="nav-section-title">{t(section.title)}</div>
              )}
              {section.items.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`nav-item${active === item.key ? ' active' : ''}`}
                  onClick={() => {
                    onSelect(item.key);
                    onClose?.();
                  }}
                  aria-current={active === item.key ? 'page' : undefined}
                >
                  <span className="nav-icon" aria-hidden="true">
                    {item.icon}
                  </span>
                  <span>{t(item.label)}</span>
                  {item.count > 0 && (
                    <span className={`nav-count${item.muted ? ' muted' : ''}`}>
                      {item.count}
                    </span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          {t('Persistent · Provenance-preserving · Consent-aware')}
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
