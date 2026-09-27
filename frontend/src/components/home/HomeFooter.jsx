import { Link } from 'react-router-dom';
import { BrandMark } from './illustrations';
import { scrollToSection } from './HomeNav';
import { useT } from '../../i18n/LanguageContext';

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'Health Memory', section: 'health-memory' },
      { label: 'How It Works', section: 'how-it-works' },
      { label: 'AI Assistance', section: 'intelligence' },
      { label: 'Emergency Card', section: 'emergency' },
    ],
  },
  {
    title: 'For Care Teams',
    links: [
      { label: 'Doctors', section: 'for-doctors' },
      { label: 'Caregivers', section: 'for-caregivers' },
      { label: 'Old Age Homes', section: 'for-caregivers' },
      { label: 'Reviewers', section: 'for-reviewers' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', section: 'about' },
      { label: 'Contact', section: 'about' },
      { label: 'Privacy', section: 'about' },
      { label: 'Terms', section: 'about' },
    ],
  },
];

export function HomeFooter() {
  const t = useT();

  return (
    <footer className="hp-footer" id="about">
      <div className="hp-shell">
        <div className="hp-footer-top">
          <div className="hp-footer-about">
            <div className="hp-brand">
              <span className="hp-brand-mark">
                <BrandMark size={22} />
              </span>
              <span className="hp-brand-text">
                <span className="hp-brand-name">{t('Health Memory')}</span>
                <span className="hp-brand-sub">{t('Elder Care Platform')}</span>
              </span>
            </div>
            <p>
              {t(
                'A persistent, consent-aware health memory that keeps an elderly patient’s health story connected across every doctor, caregiver and reviewer that supports them.',
              )}
            </p>
          </div>

          {COLUMNS.map((column) => (
            <div key={column.title}>
              <h4>{t(column.title)}</h4>
              <ul>
                {column.links.map((link) => (
                  <li key={link.label}>
                    <button
                      type="button"
                      onClick={() => scrollToSection(link.section)}
                    >
                      {t(link.label)}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="hp-footer-bottom">
          <span>
            {t('© {year} Health Memory · Built for connected elder care', {
              year: new Date().getFullYear(),
            })}
          </span>
          <span style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            <Link to="/login">{t('Login')}</Link>
            <Link to="/register">{t('Get Started')}</Link>
          </span>
        </div>
      </div>
    </footer>
  );
}

export default HomeFooter;
