import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BrandMark, Icon } from './illustrations';
import { useT } from '../../i18n/LanguageContext';
import LanguageToggle from '../../i18n/LanguageToggle';

export const NAV_LINKS = [
  { id: 'top', label: 'Home' },
  { id: 'how-it-works', label: 'How It Works' },
  { id: 'health-memory', label: 'Health Memory' },
  { id: 'for-doctors', label: 'For Doctors' },
  { id: 'for-caregivers', label: 'For Caregivers' },
  { id: 'for-reviewers', label: 'For Reviewers' },
  { id: 'about', label: 'About' },
];

export function scrollToSection(id) {
  if (id === 'top') {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }
  const target = document.getElementById(id);
  if (!target) return;
  const offset = 88;
  const top = target.getBoundingClientRect().top + window.scrollY - offset;
  window.scrollTo({ top, behavior: 'smooth' });
}

export function HomeNav({ user, dashboardPath }) {
  const t = useT();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [active, setActive] = useState('top');

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 8);
      const marker = window.scrollY + 160;
      let current = 'top';
      let best = -Infinity;
      NAV_LINKS.forEach((link) => {
        const node = document.getElementById(link.id);
        if (!node) return;
        // getBoundingClientRect, not offsetTop: several targets sit inside
        // positioned sections, so offsetTop is relative to the section rather
        // than the document and every one of them would look "reached".
        const top = node.getBoundingClientRect().top + window.scrollY;
        if (top <= marker && top > best) {
          best = top;
          current = link.id;
        }
      });
      setActive(window.scrollY < 200 ? 'top' : current);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  const go = (id) => {
    setMenuOpen(false);
    // Let the menu close before measuring the scroll target.
    window.requestAnimationFrame(() => scrollToSection(id));
  };

  return (
    <>
      <header className={`hp-nav${scrolled ? ' scrolled' : ''}`}>
        <div className="hp-shell hp-nav-inner">
          <button
            type="button"
            className="hp-brand"
            onClick={() => go('top')}
            style={{ border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}
            aria-label={t('Elder Health Memory — back to top')}
          >
            <span className="hp-brand-mark">
              <BrandMark size={22} />
            </span>
            <span className="hp-brand-text">
              <span className="hp-brand-name">{t('Health Memory')}</span>
              <span className="hp-brand-sub">{t('Elder Care Platform')}</span>
            </span>
          </button>

          <nav className="hp-nav-links" aria-label={t('Primary')}>
            {NAV_LINKS.map((link) => (
              <button
                key={link.id}
                type="button"
                className={`hp-nav-link${active === link.id ? ' active' : ''}`}
                onClick={() => go(link.id)}
              >
                {t(link.label)}
              </button>
            ))}
          </nav>

          <div className="hp-nav-actions">
            <LanguageToggle compact />
            {user ? (
              <Link className="hp-btn hp-btn-primary hp-btn-sm" to={dashboardPath}>
                {t('Open my dashboard')}
                <Icon name="arrowRight" size={17} />
              </Link>
            ) : (
              <>
                <Link className="hp-btn hp-btn-ghost hp-btn-sm" to="/login">
                  {t('Login')}
                </Link>
                <Link className="hp-btn hp-btn-primary hp-btn-sm" to="/register">
                  {t('Get Started')}
                </Link>
              </>
            )}
            <button
              type="button"
              className={`hp-nav-toggle${menuOpen ? ' open' : ''}`}
              onClick={() => setMenuOpen((open) => !open)}
              aria-label={menuOpen ? t('Close menu') : t('Open menu')}
              aria-expanded={menuOpen}
            >
              <span />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="hp-mobile-menu" id="hp-mobile-menu">
          {NAV_LINKS.map((link) => (
            <button
              key={link.id}
              type="button"
              className="hp-mobile-link"
              onClick={() => go(link.id)}
            >
              {t(link.label)}
              <Icon name="arrowRight" size={18} />
            </button>
          ))}
          <div className="hp-mobile-cta">
            <LanguageToggle />
            {user ? (
              <Link className="hp-btn hp-btn-primary" to={dashboardPath}>
                {t('Open my dashboard')}
              </Link>
            ) : (
              <>
                <Link className="hp-btn hp-btn-primary" to="/register">
                  {t('Get Started')}
                </Link>
                <Link className="hp-btn hp-btn-ghost" to="/login">
                  {t('Login')}
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default HomeNav;
