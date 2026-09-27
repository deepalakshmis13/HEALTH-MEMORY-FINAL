import { useT } from '../../i18n/LanguageContext';

export function PageHeader({ icon, title, subtitle, actions, badge }) {
  const t = useT();
  return (
    <header className="page-header">
      <div className="ph-text">
        <h1>
          {icon && <span aria-hidden="true">{icon}</span>}
          <span>{t(title)}</span>
          {badge}
        </h1>
        {subtitle && <p className="ph-sub">{t(subtitle)}</p>}
      </div>
      {actions && <div className="ph-actions">{actions}</div>}
    </header>
  );
}

export function SectionCard({ title, subtitle, actions, children, footer, flush }) {
  const t = useT();
  return (
    <section className="card">
      {(title || actions) && (
        <div className="card-header">
          <h3>
            {t(title)}
            {subtitle && <span className="card-sub">{t(subtitle)}</span>}
          </h3>
          {actions}
        </div>
      )}
      <div className={`card-body${flush ? ' flush' : ''}`}>{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </section>
  );
}

export default PageHeader;
