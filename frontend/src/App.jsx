import { useEffect, useState } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom';
import './App.css';

import { ToastProvider } from './components/common/Toast';
import LoadingState from './components/common/LoadingState';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import PatientDashboard from './pages/PatientDashboard';
import DoctorDashboard from './pages/DoctorDashboard';
import CaregiverDashboard from './pages/CaregiverDashboard';
import ReviewerDashboard from './pages/ReviewerDashboard';
import authService from './services/authService';
import { getToken } from './services/api';
import { defaultRouteFor } from './utils/permissions';

function Protected({ user, role, children }) {
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) {
    return <Navigate to={defaultRouteFor(user.role)} replace />;
  }
  return children;
}

function AppRoutes() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    authService
      .me()
      .then((profile) => setUser(profile))
      .catch(() => authService.logout())
      .finally(() => setReady(true));
  }, []);

  const signOut = () => {
    authService.logout();
    setUser(null);
    navigate('/login', { replace: true });
  };

  if (!ready) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <LoadingState message="Loading your health memory…" />
      </div>
    );
  }

  return (
    <Routes>
      {/*
        `/` is the public landing page. It stays reachable when signed in — the
        navigation simply swaps Login / Get Started for a link into the
        dashboard, so nobody is bounced away from the marketing site.
      */}
      <Route path="/" element={<Home user={user} />} />
      <Route
        path="/login"
        element={
          user ? (
            <Navigate to={defaultRouteFor(user.role)} replace />
          ) : (
            <Login onSignedIn={setUser} />
          )
        }
      />
      <Route
        path="/register"
        element={
          user ? (
            <Navigate to={defaultRouteFor(user.role)} replace />
          ) : (
            <Register onSignedIn={setUser} />
          )
        }
      />
      <Route
        path="/patient"
        element={
          <Protected user={user} role="patient">
            <PatientDashboard user={user} onSignOut={signOut} />
          </Protected>
        }
      />
      <Route
        path="/doctor"
        element={
          <Protected user={user} role="doctor">
            <DoctorDashboard user={user} onSignOut={signOut} />
          </Protected>
        }
      />
      <Route
        path="/caregiver"
        element={
          <Protected user={user} role="caregiver">
            <CaregiverDashboard user={user} onSignOut={signOut} />
          </Protected>
        }
      />
      <Route
        path="/reviewer"
        element={
          <Protected user={user} role="reviewer">
            <ReviewerDashboard user={user} onSignOut={signOut} />
          </Protected>
        }
      />
      <Route
        path="*"
        element={<Navigate to={user ? defaultRouteFor(user.role) : '/'} replace />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ToastProvider>
  );
}
