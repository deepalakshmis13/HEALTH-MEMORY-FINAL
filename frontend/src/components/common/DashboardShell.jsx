import { useState } from 'react';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

/** The shared shell every role dashboard sits inside. */
export function DashboardShell({
  user,
  meta,
  sections,
  active,
  onSelect,
  title,
  subtitle,
  onSignOut,
  topbarActions,
  seniorScale = false,
  children,
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`app-shell${seniorScale ? ' senior-scale' : ''}`}>
      <Sidebar
        open={open}
        onClose={() => setOpen(false)}
        user={user}
        meta={meta}
        sections={sections}
        active={active}
        onSelect={onSelect}
      />
      <div className="main-area">
        <Navbar
          title={title}
          subtitle={subtitle}
          user={user}
          actions={topbarActions}
          onToggleSidebar={() => setOpen((value) => !value)}
          onSignOut={onSignOut}
        />
        <main className="page">{children}</main>
      </div>
    </div>
  );
}

export default DashboardShell;
