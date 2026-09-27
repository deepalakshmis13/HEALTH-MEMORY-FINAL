import api, { clearSession, getStoredUser, setSession } from './api';

export const authService = {
  async login(email, password) {
    const data = await api.post('/api/auth/login', { email, password });
    setSession(data.access_token, data.user);
    return data.user;
  },

  async register(payload) {
    const data = await api.post('/api/auth/register', payload);
    setSession(data.access_token, data.user);
    return data.user;
  },

  async me() {
    return api.get('/api/auth/me');
  },

  logout() {
    clearSession();
  },

  cachedUser: getStoredUser,
};

export default authService;
