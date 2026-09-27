import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useToast } from '../components/common/Toast';
import authService from '../services/authService';
import { DEMO_FLOW } from '../data/demoData';
import { defaultRouteFor } from '../utils/permissions';
import { useT } from '../i18n/LanguageContext';
import LanguageToggle from '../i18n/LanguageToggle';

export function Login({ onSignedIn }) {
  const t = useT();
  const navigate = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const signIn = async (nextEmail, nextPassword) => {
    setBusy(true);
    setError('');
    try {
      const user = await authService.login(nextEmail, nextPassword);
      onSignedIn(user);
      toast.success(t('Signed in as {name}', { name: user.full_name }), t('Welcome back'));
      navigate(defaultRouteFor(user.role), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-screen">
      <aside className="auth-aside">
        <div>
          <h1>{t('A health memory that follows the patient, not the clinic.')}</h1>
          <p>
            {t(
              'Fragmented notes, prescriptions, voice diaries and caregiver observations become one longitudinal record — consent-aware, provenance-preserving, and safe to reason over.'
            )}
          </p>
        </div>
        <div className="auth-pipeline">
          {DEMO_FLOW.map((step, index) => (
            <div className="pl-step" key={step}>
              <span className="pl-num">{index + 1}</span>
              <span>{t(step)}</span>
            </div>
          ))}
        </div>
      </aside>

      <main className="auth-main">
        <div className="auth-form">
          <Link to="/" className="small muted" style={{ display: 'inline-block' }}>
            {t('← Back to home')}
          </Link>
          <LanguageToggle compact />
          <h1 className="mb-1 mt-2">{t('Sign in')}</h1>
          <p className="muted mb-2">
            {t(
              'Four dashboards, one shared health memory: patient, doctor, caregiver and reviewer.'
            )}
          </p>

          {error && (
            <div className="alert alert-danger mb-2">
              <span className="alert-icon" aria-hidden="true">
                ⚠️
              </span>
              <div className="alert-body">{error}</div>
            </div>
          )}

          <form
            onSubmit={(event) => {
              event.preventDefault();
              signIn(email, password);
            }}
          >
            <div className="field">
              <label htmlFor="email">{t('Email address')}</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                autoComplete="username"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">{t('Password')}</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={busy}
            >
              {busy ? t('Signing in…') : t('Sign in')}
            </button>
          </form>

          <p className="small muted mt-2 center">
            {t('New here?')} <Link to="/register">{t('Create an account')}</Link>
          </p>

          <p className="tiny faint mt-3 center">
            {t(
              'Access is granted per account. Doctors, caregivers and reviewers see a patient’s health memory only where the patient has granted consent.'
            )}
          </p>
        </div>
      </main>
    </div>
  );
}

export default Login;
