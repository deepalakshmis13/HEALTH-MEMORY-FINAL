import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useToast } from '../components/common/Toast';
import authService from '../services/authService';
import { ROLES } from '../utils/constants';
import { defaultRouteFor } from '../utils/permissions';
import { useT } from '../i18n/LanguageContext';
import LanguageToggle from '../i18n/LanguageToggle';

export function Register({ onSignedIn }) {
  const t = useT();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'patient',
    phone: '',
    age: '',
    gender: '',
    blood_group: '',
    guardian_name: '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const update = (patch) => setForm((current) => ({ ...current, ...patch }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const payload = {
        ...form,
        age: form.age ? Number(form.age) : null,
      };
      const user = await authService.register(payload);
      onSignedIn(user);
      toast.success(t('Your health memory has been created.'), t('Account created'));
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
          <h1>{t('Start a persistent health memory.')}</h1>
          <p>
            {t(
              'A new patient record begins with an explicit consent configuration: nothing is shared with a doctor, caregiver or reviewer until it is granted, and every change is written to the audit log.'
            )}
          </p>
        </div>
      </aside>

      <main className="auth-main">
        <div className="auth-form">
          <Link to="/" className="small muted" style={{ display: 'inline-block' }}>
            {t('← Back to home')}
          </Link>
          <LanguageToggle compact />
          <h1 className="mb-1 mt-2">{t('Create an account')}</h1>
          <p className="muted mb-2">
            {t('Choose the role you will use this platform in.')}
          </p>

          {error && (
            <div className="alert alert-danger mb-2">
              <span className="alert-icon" aria-hidden="true">
                ⚠️
              </span>
              <div className="alert-body">{error}</div>
            </div>
          )}

          <form onSubmit={submit}>
            <div className="field">
              <span className="form-label">{t('Role')}</span>
              <div className="row tight">
                {Object.entries(ROLES).map(([key, role]) => (
                  <button
                    key={key}
                    type="button"
                    className={`chip${form.role === key ? ' active' : ''}`}
                    onClick={() => update({ role: key })}
                  >
                    {role.icon} {t(role.label)}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label htmlFor="full_name">{t('Full name')}</label>
              <input
                id="full_name"
                value={form.full_name}
                onChange={(event) => update({ full_name: event.target.value })}
                required
              />
            </div>

            <div className="grid grid-2">
              <div className="field">
                <label htmlFor="reg-email">{t('Email address')}</label>
                <input
                  id="reg-email"
                  type="email"
                  value={form.email}
                  onChange={(event) => update({ email: event.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="reg-password">{t('Password')}</label>
                <input
                  id="reg-password"
                  type="password"
                  value={form.password}
                  onChange={(event) => update({ password: event.target.value })}
                  minLength={6}
                  required
                />
              </div>
            </div>

            {form.role === 'patient' && (
              <div className="grid grid-3">
                <div className="field">
                  <label htmlFor="age">{t('Age')}</label>
                  <input
                    id="age"
                    type="number"
                    min="0"
                    max="120"
                    value={form.age}
                    onChange={(event) => update({ age: event.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="gender">{t('Gender')}</label>
                  <select
                    id="gender"
                    value={form.gender}
                    onChange={(event) => update({ gender: event.target.value })}
                  >
                    <option value="">{t('Prefer not to say')}</option>
                    <option value="Female">{t('Female')}</option>
                    <option value="Male">{t('Male')}</option>
                    <option value="Other">{t('Other')}</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="blood">{t('Blood group')}</label>
                  <select
                    id="blood"
                    value={form.blood_group}
                    onChange={(event) => update({ blood_group: event.target.value })}
                  >
                    <option value="">{t('Unknown')}</option>
                    {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((group) => (
                      <option key={group}>{group}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {form.role === 'patient' && (
              <div className="field">
                <label htmlFor="guardian">{t('Guardian name (optional)')}</label>
                <input
                  id="guardian"
                  value={form.guardian_name}
                  onChange={(event) => update({ guardian_name: event.target.value })}
                />
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary btn-lg btn-block"
              disabled={busy}
            >
              {busy ? t('Creating your account…') : t('Create account')}
            </button>
          </form>

          <p className="small muted mt-2 center">
            {t('Already have an account?')} <Link to="/login">{t('Sign in')}</Link>
          </p>
        </div>
      </main>
    </div>
  );
}

export default Register;
