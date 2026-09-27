import { ROLES } from '../../utils/constants';
import { initials } from '../../utils/formatters';
import { useT } from '../../i18n/LanguageContext';
import LanguageToggle from '../../i18n/LanguageToggle';

export function Navbar({ title, subtitle, user, onToggleSidebar, onSignOut, actions }) {
  const t = useT();

  return (
    <header className="topbar">
      <button
        type="button"
        className="menu-toggle"
        onClick={onToggleSidebar}
        aria-label={t('Open navigation menu')}
      >
        ☰
      </button>
      <div className="topbar-titles">
        <div className="topbar-title">{t(title)}</div>
        {subtitle && <div className="topbar-sub">{t(subtitle)}</div>}
      </div>
      <div className="topbar-spacer" />
      <LanguageToggle compact />
      {actions}
      <div className="topbar-user">
        <div className="avatar" aria-hidden="true">
          {initials(user?.full_name)}
        </div>
        <div className="hide-sm" style={{ lineHeight: 1.25 }}>
          <div className="small strong nowrap">{user?.full_name}</div>
          <div className="tiny muted nowrap">
            {t(ROLES[user?.role]?.label || user?.role)}
          </div>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onSignOut}>
          {t('Sign out')}
        </button>
      </div>
    </header>
  );
}

export default Navbar;
